"""Reading context regressions: broken dependencies must not silently publish."""
import copy
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/math-logic-mindmap/scripts'))
from math_logic_mindmap.common import Invalid, read_json, write_json
from math_logic_mindmap.model import estimate, validate
from math_logic_mindmap.render import card, generate_notes, input_table
from math_logic_mindmap.readability import validate_inline_math, validate_readability, resolve
from math_logic_mindmap import bundle


class ReadingTests(unittest.TestCase):
    def setUp(self):
        self.model = read_json(ROOT / 'tests/fixtures/canonical-smoke.proof.json')
        self.nodes = {n['id']: n for n in self.model['nodes']}

    def test_multiline_card_full_summary_and_legacy_default(self):
        node = copy.deepcopy(self.nodes['A1'])
        original = node['formula_latex']
        self.assertIn(original, card(node, self.model['slug']))
        multiline = (r'\left\{\begin{aligned}x&>0\\x&<2\\x&\in\mathbb{R}\end{aligned}\right.')
        node['formula_latex'] = multiline
        self.assertLessEqual(estimate(node)['height'], 480)
        self.assertIn(multiline, card(node, self.model['slug']))
        node['card_formula_display'] = 'summary'
        self.assertNotIn(multiline, card(node, self.model['slug']))
        self.assertIn(node['short_role'], card(node, self.model['slug']))
        self.assertLess(estimate(node)['height'], 480)
        invalid = copy.deepcopy(self.model)
        invalid['nodes'][0]['card_formula_display'] = 'abridged'
        with self.assertRaisesRegex(Invalid, 'SCHEMA'):
            validate(invalid)

    def test_multiline_edge_summary_is_not_inline_math(self):
        model = copy.deepcopy(self.model)
        source = next(n for n in model['nodes'] if n['id'] == 'A1')
        latex = r'\left\{\begin{aligned}x&>0\\x&<2\end{aligned}\right.'
        source['formula_latex'] = latex
        next(b for s in source['sections'] for b in s['blocks'] if b['kind'] == 'formula')['latex'] = latex
        combine = next(n for n in model['nodes'] if n['id'] == 'C1')
        next(b for b in combine['derivation'] if b.get('id') == 'input1')['latex'] = latex
        edge = next(e for e in model['edges'] if e['source'] == 'A1')
        edge['detail_mode'] = 'EDGE_DETAIL'
        edge['label_text'] = '条件传递'
        edge['detail'] = {'summary': '摘要', 'source_contribution': '贡献', 'transition_steps': ['转换'],
                          'target_gain': '所得', 'conditions': [], 'condition_checks': [],
                          'role_in_proof': '作用'}
        note = generate_notes(model)[f'note/{model["slug"]}/{edge["id"]}.md']
        self.assertIn('$$\n' + latex + '\n$$', note)
        self.assertNotIn('$' + latex + '$', note)

    def test_every_note_navigation_and_combine_order(self):
        notes = generate_notes(self.model)
        order = ['导航', '输入回顾', '合并动机与意义', '合并思路与工具', '详细推导', '合并结果', '传入关系', '传出关系', '个人补充']
        slug = self.model['slug']
        for nid, node in self.nodes.items():
            text = notes[f'note/{slug}/{nid}.md']
            self.assertIn('## 导航\n', text)
            if node['type'] == 'COMBINE':
                offsets = [text.index('## ' + h + '\n') for h in order]
                self.assertEqual(offsets, sorted(offsets))
                derivation = text.split('## 详细推导\n')[1].split('## 合并结果\n')[0]
                result = text.split('## 合并结果\n')[1].split('## 适用条件与核验\n')[0]
                display = '$$\n' + node['combine_output_latex'] + '\n$$'
                self.assertNotIn(display, derivation)
                self.assertEqual(result.count(display), 1)

    def test_feature_edge_notes_are_nonempty_and_reachable_from_both_ends(self):
        model = read_json(ROOT / 'tests/fixtures/feature-coverage.proof.json')
        notes = generate_notes(model)
        slug = model['slug']
        detail_edges = [edge for edge in model['edges'] if edge['detail_mode'] == 'EDGE_DETAIL']
        edge_notes = {path: text for path, text in notes.items()
                      if re.fullmatch(rf'note/{slug}/E[^/]+\.md', path)}
        self.assertGreater(len(detail_edges), 0)
        self.assertEqual(set(edge_notes), {f'note/{slug}/{edge["id"]}.md' for edge in detail_edges})
        for edge in detail_edges:
            path = f'note/{slug}/{edge["id"]}.md'
            self.assertIn('## 导航\n', edge_notes[path])
            link = f'[[note/{slug}/{edge["id"]}|{edge["id"]} · {edge["label_text"]}]]'
            for endpoint in (edge['source'], edge['target']):
                with self.subTest(edge=edge['id'], endpoint=endpoint):
                    self.assertIn(link, notes[f'note/{slug}/{endpoint}.md'])
        discharge = edge_notes[f'note/{slug}/EN2T1.md']
        self.assertIn('解除局部假设：[[note/feature-coverage/H1|H1]]', discharge)

    def test_feature_fixture_builds_scope_and_edge_notes_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = read_json(ROOT / 'tests/fixtures/feature-coverage.proof.json')
            slug = model['slug']
            path = root / 'proof' / slug / f'{slug}.proof.json'
            write_json(path, model)
            result = bundle.build(root, path)
            self.assertEqual(result['machine'], 'PASS')
            stage = root / '.build/staging' / slug
            self.assertTrue((stage / f'note/{slug}/EN2T1.md').is_file())
            canvas = read_json(stage / f'mindmap/{slug}.canvas')
            self.assertIn('GL1', {node['id'] for node in canvas['nodes'] if node['type'] == 'group'})

    def test_neighbour_combine_exposes_siblings_and_expanded_output(self):
        note = generate_notes(self.model)[f'note/{self.model["slug"]}/A1.md']
        part = note.split('## 传出关系\n')[1]
        self.assertIn(self.nodes['A1']['formula_latex'], part)
        self.assertIn(self.nodes['A2']['formula_latex'], part)
        expanded = resolve(self.nodes, 'N1', 'core')['latex']
        self.assertIn(expanded, part)
        self.assertNotIn('使用依据：', part)  # no recursive full derivation

    def test_source_changes_update_review_but_reject_stale_use(self):
        source = resolve(self.nodes, 'A2', 'core')['latex'] + r'\quad'
        self.nodes['A2']['formula_latex'] = source
        next(b for s in self.nodes['A2']['sections'] for b in s['blocks'] if b['kind']=='formula')['latex'] = source
        self.assertIn(source, input_table(self.model, self.nodes['C1']))
        with self.assertRaisesRegex(Invalid, 'READING-USE'):
            validate(self.model)

    def test_missing_and_invalid_input_records(self):
        for case in ('missing', 'duplicate', 'reference', 'step', 'start', 'shared_step'):
            model = copy.deepcopy(self.model)
            c = next(n for n in model['nodes'] if n['id'] == 'C1')
            if case == 'missing': c['input_usage'].pop()
            elif case == 'duplicate': c['input_review'].append(copy.deepcopy(c['input_review'][0]))
            elif case == 'reference': c['input_review'][0]['formula_ref'] = 'absent'
            elif case == 'step': c['input_usage'][0]['step_id'] = 'absent'
            elif case == 'start': c['start_input'] = 'A2'
            else: c['input_usage'][1]['step_id'] = c['input_usage'][0]['step_id']
            with self.subTest(case=case), self.assertRaises(Invalid):
                validate(model)

    def test_missing_navigation_and_reserved_headings(self):
        for case in ('navigation', 'heading', 'stage', 'stage_nodes', 'formula_id'):
            model = copy.deepcopy(self.model)
            n = model['nodes'][0]
            if case == 'navigation': n.pop('navigation')
            elif case == 'heading': n['sections'][0]['heading'] = '导航'
            elif case == 'stage': n['navigation']['stage'] = 'absent'
            elif case == 'stage_nodes': model['proof_flow'][0]['nodes'].pop()
            else:
                block = next(b for s in n['sections'] for b in s['blocks'] if b['kind'] == 'formula')
                n['sections'][0]['blocks'].append(copy.deepcopy(block))
            with self.subTest(case=case), self.assertRaises(Invalid):
                validate(model)

    def test_math_bars_rejected_before_markdown_escaping(self):
        self.nodes['A2']['formula_latex'] = '|z|'
        next(b for s in self.nodes['A2']['sections'] for b in s['blocks'] if b['kind']=='formula')['latex'] = '|z|'
        use = next(b for b in self.nodes['C1']['derivation'] if b.get('id') == 'input2')
        use['latex'] = '|z|'
        with self.assertRaisesRegex(Invalid, 'TABLE-BAR'):
            validate(self.model)

    def test_bare_inline_math_is_rejected_with_field_path(self):
        cases = (
            (r'u\le v', r'model/theorem/assumptions/0'),
            ('x_i', r'model/theorem/assumptions/0'),
            ('x^2', r'model/theorem/assumptions/0'),
            ('2^n', r'model/theorem/assumptions/0'),
            ('λ', r'model/theorem/assumptions/0'),
            ('ℝ', r'model/theorem/assumptions/0'),
            ('x∈I', r'model/theorem/assumptions/0'),
            ('c>0', r'model/theorem/assumptions/0'),
            ('P(m-1)', r'model/theorem/assumptions/0'),
            ('f(x)', r'model/theorem/assumptions/0'),
            ('Q(n)', r'model/theorem/assumptions/0'),
            ('sin(x)', r'model/theorem/assumptions/0'),
            ('x+y', r'model/theorem/assumptions/0'),
            ('x-y', r'model/theorem/assumptions/0'),
            ('x/n', r'model/theorem/assumptions/0'),
            ('1/n', r'model/theorem/assumptions/0'),
            ('|x|', r'model/theorem/assumptions/0'),
            ("x'", r'model/theorem/assumptions/0'),
        )
        for value, path in cases:
            model = copy.deepcopy(self.model)
            model['theorem']['assumptions'][0] = value
            with self.subTest(value=value), self.assertRaisesRegex(Invalid, rf'MATH-INLINE {path}'):
                validate_inline_math(model)

    def test_inline_math_delimiters_are_checked(self):
        for value in ('$x', '$$', '$ x $', '$x $'):
            model = copy.deepcopy(self.model)
            model['theorem']['assumptions'][0] = value
            with self.subTest(value=value), self.assertRaisesRegex(Invalid, 'MATH-INLINE-DELIMITER model/theorem/assumptions/0'):
                validate_inline_math(model)
        model = copy.deepcopy(self.model)
        model['context']['背景'] = r'价格写作 \$5；字面源码写作 `x_i`；参见 [来源](https://example.test/?a=b) 和 https://example.test/?p_i=1；字段名 proof_flow。'
        validate_inline_math(model)

    def test_inline_math_rejects_control_characters_without_banning_prose_line_breaks(self):
        for value in ('$b\ne0$', '$x\times y$', '$x' + chr(0) + 'y$'):
            model = copy.deepcopy(self.model)
            model['theorem']['assumptions'][0] = value
            with self.subTest(value=repr(value)), self.assertRaisesRegex(
                    Invalid, 'MATH-INLINE-CONTROL model/theorem/assumptions/0'):
                validate_inline_math(model)

        model = copy.deepcopy(self.model)
        model['theorem']['assumptions'][0] = 'First ' + r'$b\ne0$' + '.\nSecond line.'
        validate_inline_math(model)

    def test_inline_math_diagnostics_explain_literal_code_and_currency(self):
        model = copy.deepcopy(self.model)
        model['theorem']['assumptions'][0] = '标识符 x_axis。'
        with self.assertRaises(Invalid) as raised:
            validate_inline_math(model)
        self.assertIn('backticks', str(raised.exception))

        model = copy.deepcopy(self.model)
        model['theorem']['assumptions'][0] = '$5 与 $10'
        with self.assertRaises(Invalid) as raised:
            validate_inline_math(model)
        self.assertIn(r'\$', str(raised.exception))

    def test_plain_text_rendering_context_rejects_math_markup(self):
        model = copy.deepcopy(self.model)
        model['edges'][0]['label_text'] = '$x$'
        with self.assertRaisesRegex(Invalid, 'MATH-PLAIN-TEXT model/edges/.*/label_text'):
            validate_inline_math(model)
        model = copy.deepcopy(self.model)
        operation = next(node for node in model['nodes'] if node.get('derivation_chain'))
        next(row for row in operation['derivation_chain']['rows'] if row.get('name'))['name'] = 'x_i'
        with self.assertRaisesRegex(Invalid, 'MATH-PLAIN-TEXT model/nodes/.*/derivation_chain/rows/.*/name'):
            validate_inline_math(model)

    def test_link_and_anchor_titles_are_plain_text(self):
        cases = (
            ('node-dollar', 'MATH-PLAIN-TEXT model/nodes/0/title'),
            ('node-formula', 'MATH-PLAIN-TEXT model/nodes/0/title'),
            ('stage-dollar', 'MATH-PLAIN-TEXT model/proof_flow/0/title'),
            ('stage-formula', 'MATH-PLAIN-TEXT model/proof_flow/0/title'),
        )
        for case, path in cases:
            model = copy.deepcopy(self.model)
            if case.startswith('node'):
                model['nodes'][0]['title'] = '$x$' if case.endswith('dollar') else 'f(x)'
            else:
                model['proof_flow'][0]['title'] = '$x$' if case.endswith('dollar') else 'f(x)'
            with self.subTest(case=case), self.assertRaisesRegex(Invalid, path):
                validate_inline_math(model)

    def test_markdown_roles_and_summaries_keep_inline_math(self):
        model = copy.deepcopy(self.model)
        model['nodes'][0]['short_role'] = '说明 $x$ 的作用。'
        model['proof_flow'][0]['summary'] = '处理 $x$。'
        self.assertEqual(validate_inline_math(model), [])
        notes = generate_notes(model)
        slug = model['slug']
        self.assertIn('说明 $x$ 的作用。', card(model['nodes'][0], slug, model))
        index = notes[f'note/{slug}/index.md']
        self.assertIn('处理 $x$。', index)
        for stage in model['proof_flow']:
            self.assertIn(f'### 阶段 {stage["id"]} · {stage["title"]}', index)
        for node in model['nodes']:
            alias = f'[[note/{slug}/{node["id"]}|{node["id"]} · {node["title"]}]]'
            self.assertIn(alias, index)
            self.assertNotIn('$', alias)

    def test_neutral_fixtures_have_no_inline_math_warnings(self):
        for name in ('canonical-smoke', 'feature-coverage'):
            model = read_json(ROOT / f'tests/fixtures/{name}.proof.json')
            with self.subTest(name=name):
                self.assertEqual(validate_inline_math(model), [])

    def test_ambiguous_inline_math_warning_is_language_scoped(self):
        model = copy.deepcopy(self.model)
        model['context']['背景'] = '构造 z，并保持节点≤20。'
        warnings = validate_inline_math(model)
        self.assertTrue(any('isolated letter z' in warning for warning in warnings))
        self.assertTrue(any('bare symbol ≤' in warning for warning in warnings))
        for language in ('en', 'fr'):
            translated = copy.deepcopy(self.model)
            translated['presentation']['language'] = language
            translated['context']['背景'] = 'Use a temporary variable.'
            with self.subTest(language=language):
                self.assertFalse(any('isolated letter' in warning for warning in validate_inline_math(translated)))

    def test_spaced_math_function_warns_but_numeric_date_passes(self):
        model = copy.deepcopy(self.model)
        model['theorem']['assumptions'][0] = '使用 sin x 估计。'
        warnings = validate_inline_math(model)
        self.assertTrue(any('bare function notation sin x' in warning for warning in warnings))

        model = copy.deepcopy(self.model)
        model['theorem']['assumptions'][0] = '记录日期为 2026/09。'
        self.assertEqual(validate_inline_math(model), [])

    def test_long_formula_has_full_path_same_page_anchor(self):
        long_latex = '+'.join(f'a_{{{i}}}' for i in range(1, 26))
        self.nodes['A1']['formula_latex'] = long_latex
        next(b for s in self.nodes['A1']['sections'] for b in s['blocks'] if b['kind']=='formula')['latex'] = long_latex
        next(b for b in self.nodes['C1']['derivation'] if b.get('id')=='input1')['latex'] = long_latex
        text = generate_notes(self.model)[f'note/{self.model["slug"]}/A1.md']
        self.assertIn(rf'[[note/{self.model["slug"]}/A1#输入公式 C1 A1\|完整公式见下方]]', text)
        table_lines = [line for line in text.splitlines() if line.startswith('|')]
        self.assertTrue(all(r'\begin{aligned}' not in line for line in table_lines))
        self.assertIn('#### 输入公式 C1 A1\n\n$$\n', text)

    def test_table_links_pass_bundle_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = read_json(ROOT / 'tests/fixtures/canonical-smoke.proof.json')
            path = root / 'proof/canonical-smoke/canonical-smoke.proof.json'
            write_json(path, model)
            result = bundle.build(root, path)
            self.assertEqual(result['machine'], 'PASS')

    def test_incomplete_reading_model_is_rejected(self):
        old = copy.deepcopy(self.model)
        old.pop('proof_flow')
        for n in old['nodes']: n.pop('navigation')
        with self.assertRaisesRegex(Invalid, 'SCHEMA'):
            validate(old)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'proof' / old['slug'] / f'{old["slug"]}.proof.json'
            write_json(path, old)
            with self.assertRaisesRegex(Invalid, 'SCHEMA'):
                bundle.build(Path(directory), path)

    def test_bound_condition_is_boxed(self):
        text = generate_notes(self.model)[f'note/{self.model["slug"]}/C1.md']
        source = resolve(self.nodes, 'A2', 'core')['latex']
        self.assertIn(source, text)
        self.assertIn(r'\right\downarrow\qquad \boxed{', text)

    def test_formula_reference_is_local(self):
        self.nodes['C1']['input_review'][0]['formula_ref'] = 'A2/core'
        with self.assertRaisesRegex(Invalid, 'READING-REF'):
            validate_readability(self.model)

    def test_text_only_node_and_condition_input(self):
        n = self.nodes['A2']
        n['formula_latex'] = None
        n['sections'] = [{'heading': '数据范围', 'blocks': [{'kind': 'prose', 'id': 'statement', 'text': '所有取值点都属于给定区间。'}]}]
        c = self.nodes['C1']
        usage = next(u for u in c['input_usage'] if u['node'] == 'A2')
        usage['mode'] = 'condition'
        index = next(i for i,b in enumerate(c['derivation']) if b.get('id') == usage['step_id'])
        c['derivation'][index] = {**n['sections'][0]['blocks'][0], 'id': usage['step_id']}
        validate(self.model)
        notes = generate_notes(self.model)
        slug = self.model['slug']
        self.assertIn('所有取值点都属于给定区间。', notes[f'note/{slug}/C1.md'])
        self.assertIn('所有取值点都属于给定区间。', notes[f'note/{slug}/A2.md'])


if __name__ == '__main__':
    unittest.main()
