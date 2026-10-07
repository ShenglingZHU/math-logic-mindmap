"""Human-first models keep every strict dependency visible and auditable."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/math-logic-mindmap/scripts'))
from math_logic_mindmap.common import Invalid, read_json
from math_logic_mindmap.human import granularity_report, granularity_warning
from math_logic_mindmap.model import estimate, validate
from math_logic_mindmap.render import generate_notes, layout


class HumanFirstTests(unittest.TestCase):
    def setUp(self):
        self.model = read_json(ROOT / 'tests/fixtures/canonical-smoke.proof.json')
        self.feature = read_json(ROOT / 'tests/fixtures/feature-coverage.proof.json')

    def test_combine_inputs_exactly_match_predecessors(self):
        validate(self.model)
        c1 = next(n for n in self.model['nodes'] if n['id'] == 'C1')
        self.assertEqual(set(c1['combine_inputs']), {'A1', 'A2'})
        broken = copy.deepcopy(self.model)
        next(n for n in broken['nodes'] if n['id'] == 'C1')['combine_inputs'].pop()
        with self.assertRaisesRegex(Invalid, 'combine_inputs'):
            validate(broken)

    def test_feature_fixture_covers_three_input_combines_and_support(self):
        validate(self.feature)
        nodes = {node['id']: node for node in self.feature['nodes']}
        edges = self.feature['edges']
        combines = [node for node in self.feature['nodes'] if node['type'] == 'COMBINE']
        self.assertEqual([node['id'] for node in combines], ['C1', 'C2'])
        for combine in combines:
            incoming = [edge for edge in edges if edge['target'] == combine['id']]
            outgoing = [edge for edge in edges if edge['source'] == combine['id']]
            self.assertEqual(len(incoming), 3)
            self.assertTrue(all(edge['relation'] == 'FEEDS_COMBINE' for edge in incoming))
            self.assertEqual(len(outgoing), 1)
            self.assertTrue(nodes[outgoing[0]['target']]['result'])
        self.assertEqual(self.feature['presentation']['support'], ['K1', 'K2'])
        self.assertGreaterEqual(len(self.feature['proof_flow']), 6)

    def test_feature_scope_discharge_and_presentation_fail_closed(self):
        cases = []

        missing_discharge = copy.deepcopy(self.feature)
        next(edge for edge in missing_discharge['edges'] if edge['id'] == 'EN2T1').pop('discharges')
        cases.append(('missing-discharge', missing_discharge, 'SCOPE-CLOSE'))

        wrong_discharge = copy.deepcopy(self.feature)
        next(edge for edge in wrong_discharge['edges'] if edge['id'] == 'EN2T1')['discharges'] = ['D1']
        cases.append(('wrong-discharge', wrong_discharge, 'SCOPE-CLOSE'))

        missing_scope = copy.deepcopy(self.feature)
        next(node for node in missing_scope['nodes'] if node['id'] == 'H1').pop('scope')
        cases.append(('missing-scope', missing_scope, 'SCOPE'))

        hidden_support = copy.deepcopy(self.feature)
        next(edge for edge in hidden_support['edges'] if edge['id'] == 'EK1C1')['display_mode'] = 'REFERENCE'
        cases.append(('hidden-support', hidden_support, 'REFERENCE'))

        unclassified_support = copy.deepcopy(self.feature)
        unclassified_support['presentation']['support'].remove('K1')
        cases.append(('unclassified-support', unclassified_support, 'PRESENTATION'))

        for name, model, error in cases:
            with self.subTest(case=name), self.assertRaisesRegex(Invalid, error):
                validate(model)

    def test_every_strict_edge_is_visible(self):
        info = validate(self.model)
        canvas = layout(self.model, info, {})
        self.assertEqual({e['id'] for e in canvas['edges']}, {e['id'] for e in self.model['edges']})
        broken = copy.deepcopy(self.model)
        broken['edges'][0]['display_mode'] = 'REFERENCE'
        with self.assertRaisesRegex(Invalid, 'REFERENCE'):
            validate(broken)

    def test_granularity_findings_must_be_disposed(self):
        self.assertFalse(granularity_report(self.model)['unresolved'])
        broken = copy.deepcopy(self.model)
        broken['presentation']['granularity_reviews'] = []
        with self.assertRaisesRegex(Invalid, 'GRANULARITY'):
            validate(broken)
        broken = copy.deepcopy(self.model)
        broken['presentation']['granularity_reviews'][0]['decision'] = 'merge'
        with self.assertRaisesRegex(Invalid, 'GRANULARITY'):
            validate(broken)

    def test_stale_reviews_warn_until_the_author_removes_them(self):
        model = copy.deepcopy(self.model)
        model['presentation']['granularity_reviews'].append({
            'finding_id': 'merge-candidate-OLD', 'decision': 'retain',
            'reason': 'An obsolete result used to be retained.'})
        report = granularity_report(model)
        self.assertEqual(report['stale_reviews'], ['merge-candidate-OLD'])
        self.assertIn('merge-candidate-OLD', granularity_warning(report))
        self.assertTrue(any('merge-candidate-OLD' in w for w in validate(model)['warnings']))
        model['presentation']['granularity_reviews'].pop()
        self.assertFalse(granularity_report(model)['stale_reviews'])
        self.assertIsNone(granularity_warning(granularity_report(model)))
        self.assertFalse(any(w.startswith('GRANULARITY-REVIEW:') for w in validate(model)['warnings']))

    def test_merge_advisories_only_cover_ordinary_strict_flow_results(self):
        simple = {
            'nodes': [{'id': 'A1', 'type': 'ASSUMPTION'},
                      {'id': 'D1', 'type': 'DERIVATION'},
                      {'id': 'T1', 'type': 'TARGET'}],
            'edges': [{'id': 'E1', 'source': 'A1', 'target': 'D1',
                       'relation': 'REQUIRED_FOR', 'display_mode': 'FLOW'},
                      {'id': 'E2', 'source': 'D1', 'target': 'T1',
                       'relation': 'ESTABLISHES_TARGET', 'display_mode': 'FLOW'}],
            'presentation': {'spine': ['A1', 'D1', 'T1'], 'granularity_reviews': []},
        }

        def advisories(model):
            return granularity_report(model)['advisories']

        for node_type in ('DERIVATION', 'LEMMA', 'BOUND'):
            with self.subTest(included_type=node_type):
                case = copy.deepcopy(simple)
                case['nodes'][1]['type'] = node_type
                self.assertEqual([a['id'] for a in advisories(case)], ['merge-candidate-D1'])
                self.assertFalse(granularity_report(case)['unresolved'])

        for node_type in ('ASSUMPTION', 'DEFINITION', 'KNOWN_RESULT', 'HYPOTHESIS_LOCAL',
                          'LOCAL_INTRODUCTION', 'CONSTRUCTION', 'EXISTENCE_WITNESS',
                          'CONTRADICTION', 'TARGET', 'COMBINE', 'TRANSFORM', 'CASE', 'INTUITION'):
            with self.subTest(excluded_type=node_type):
                case = copy.deepcopy(simple)
                case['nodes'][1]['type'] = node_type
                self.assertFalse(advisories(case))

        bound = copy.deepcopy(simple)
        bound['nodes'][1]['bindings'] = [{'id': 'b1'}]
        self.assertFalse(advisories(bound))

        for relation in ('COMBINE_PRODUCES', 'TRANSFORM_PRODUCES', 'CASE_BRANCH',
                         'OPENS_SCOPE', 'DISCHARGES'):
            with self.subTest(incoming_boundary=relation):
                case = copy.deepcopy(simple)
                case['edges'][0]['relation'] = relation
                self.assertFalse(advisories(case))
        for relation in ('CASE_BRANCH', 'OPENS_SCOPE', 'DISCHARGES'):
            with self.subTest(outgoing_boundary=relation):
                case = copy.deepcopy(simple)
                case['edges'][1]['relation'] = relation
                self.assertFalse(advisories(case))

        reused = copy.deepcopy(simple)
        reused['nodes'].append({'id': 'T2', 'type': 'TARGET'})
        reused['edges'].append({'id': 'E3', 'source': 'D1', 'target': 'T2',
                                'relation': 'REQUIRED_FOR', 'display_mode': 'FLOW'})
        self.assertFalse(advisories(reused))

        reference = copy.deepcopy(simple)
        reference['nodes'].append({'id': 'I1', 'type': 'INTUITION', 'strict': False})
        reference['edges'].append({'id': 'E3', 'source': 'D1', 'target': 'I1',
                                   'relation': 'REQUIRED_FOR', 'display_mode': 'REFERENCE'})
        self.assertEqual([a['id'] for a in advisories(reference)], ['merge-candidate-D1'])

    def test_merge_advisory_requires_a_live_retain_decision(self):
        model = {
            'nodes': [{'id': 'A1', 'type': 'ASSUMPTION'},
                      {'id': 'D1', 'type': 'LEMMA'},
                      {'id': 'T1', 'type': 'TARGET'}],
            'edges': [{'source': 'A1', 'target': 'D1', 'relation': 'REQUIRED_FOR', 'display_mode': 'FLOW'},
                      {'source': 'D1', 'target': 'T1', 'relation': 'ESTABLISHES_TARGET', 'display_mode': 'FLOW'}],
            'presentation': {'spine': ['A1', 'D1', 'T1'], 'granularity_reviews': []},
        }
        advisory = granularity_report(model)['advisories'][0]
        self.assertFalse(advisory['reviewed'])
        self.assertIn('D1', granularity_warning(granularity_report(model)))
        model['presentation']['granularity_reviews'] = [
            {'finding_id': advisory['id'], 'decision': 'merge', 'reason': 'Will merge later.'}]
        self.assertFalse(granularity_report(model)['advisories'][0]['reviewed'])
        model['presentation']['granularity_reviews'][0].update(
            decision='retain', reason='This result is the stage milestone used after the scope closes.')
        self.assertTrue(granularity_report(model)['advisories'][0]['reviewed'])
        self.assertIsNone(granularity_warning(granularity_report(model)))

    def test_operation_notes_have_continuous_chains(self):
        notes = generate_notes(self.model)
        slug = self.model['slug']
        self.assertIn('### 连续主链', notes[f'note/{slug}/C1.md'])
        self.assertIn('### 连续主链', notes[f'note/{slug}/X1.md'])
        self.assertIn('正数除法保序', notes[f'note/{slug}/X1.md'])

    def test_transform_card_and_result_style(self):
        smoke = read_json(ROOT / 'tests/fixtures/canonical-smoke.proof.json')
        canvas = layout(smoke, validate(smoke), {})
        x1 = next(n for n in canvas['nodes'] if n['id'] == 'X1')
        n1 = next(n for n in canvas['nodes'] if n['id'] == 'N1')
        self.assertEqual((x1['width'], x1['height']), (240, 180))
        self.assertIn('TRANSFORM', x1['text'])
        self.assertEqual(x1['styleAttributes']['shape'], 'rectangle')
        self.assertEqual(n1['styleAttributes']['proofResult'], 'true')
        self.assertEqual(n1['color'], '#CFE8CC')
        css = (ROOT / '.obsidian/snippets/math-logic-mindmap.css').read_text(encoding='utf-8')
        self.assertIn('.canvas-node[data-proof-role="TRANSFORM"] .canvas-node-content::before', css)
        self.assertNotIn('clip-path', css)

    def test_formula_width_calibration(self):
        cases = json.loads((ROOT / 'tests/fixtures/formula-width-calibration.json').read_text(encoding='utf-8'))
        for case in cases:
            node = {'id': case['case_id'], 'type': 'LEMMA', 'title': '宽度校准',
                    'short_role': '使用实际 MathJax 样本校验安全余量。',
                    'formula_latex': case['latex']}
            with self.subTest(case=case['case_id']):
                result = estimate(node)
                self.assertGreaterEqual(result['width'] - 40, case['measured_width'] * 1.1)
                self.assertEqual(result['width'], case['expected_card_width'])

    def test_oversize_formula_suggests_author_wrap(self):
        node = copy.deepcopy(next(n for n in self.model['nodes'] if n['id'] == 'A1'))
        node['formula_latex'] = r'a_1+a_2+a_3+a_4+a_5+a_6+a_7+a_8\quad' * 4
        risks = estimate(node)['risk']
        self.assertTrue(any('CARD-WRAP-SUGGESTION' in risk for risk in risks))
        self.assertTrue(any('FORMULA-WIDTH-RISK' in risk for risk in risks))

    def test_unknown_fields_are_rejected(self):
        unknown = copy.deepcopy(self.model)
        unknown['unexpected'] = True
        with self.assertRaisesRegex(Invalid, 'Additional properties'):
            validate(unknown)

        unknown_node = copy.deepcopy(self.model)
        unknown_node['nodes'][0]['unexpected'] = True
        with self.assertRaisesRegex(Invalid, 'Additional properties'):
            validate(unknown_node)


if __name__ == '__main__':
    unittest.main()
