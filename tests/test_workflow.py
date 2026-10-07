"""Regression tests use isolated vaults; review evidence here is synthetic only."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/math-logic-mindmap/scripts'))
from math_logic_mindmap import bundle
from math_logic_mindmap.cli import status_report, sync_skills
from math_logic_mindmap.common import Invalid, read_json, write_json, write_text, PERSONAL_END
from math_logic_mindmap.model import validate, model_identity, _has_top_level_symbol_separator, _check_symbol_rows
from math_logic_mindmap.render import generate_notes


class Workflow(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.slug = 'canonical-smoke'
        self.model = read_json(ROOT / 'tests/fixtures/canonical-smoke.proof.json')
        self.proof_dir = self.root / 'proof/canonical-smoke'
        self.path = self.proof_dir / 'canonical-smoke.proof.json'
        write_json(self.path, self.model)

    def publish(self):
        bundle.build(self.root, self.path)
        return bundle.release(self.root, self.slug)

    def test_root_alias_preserves_artifacts_identity_and_status(self):
        self.publish()
        root = self.root.resolve()
        paths = bundle.artifact_paths(root, self.slug)
        identity = bundle.presentation_identity(root)
        state = bundle.status(root, self.slug)
        self.assertEqual(state['machine'], 'PASS')
        with tempfile.TemporaryDirectory() as directory:
            aliases = [root / 'note' / '..']
            if os.name == 'posix':
                link = Path(directory) / 'vault'
                link.symlink_to(root, target_is_directory=True)
                aliases.append(link)
            for alias in aliases:
                with self.subTest(alias=str(alias)):
                    self.assertEqual(alias.resolve(), root)
                    actual = bundle.artifact_paths(alias, self.slug)
                    self.assertEqual(actual, paths)
                    self.assertTrue(all(not Path(p).is_absolute() and '..' not in Path(p).parts
                                        for p in actual))
                    self.assertEqual(bundle.presentation_identity(alias), identity)
                    self.assertEqual(bundle.status(alias, self.slug), state)

    def test_module_alias_preserves_source_presentation_identity(self):
        script = (
            'import json, sys; from pathlib import Path; '
            'sys.path.insert(0, sys.argv[1]); '
            'from math_logic_mindmap.bundle import presentation_identity; '
            'print(json.dumps(presentation_identity(Path(sys.argv[2]))))'
        )

        def identity(scripts):
            completed = subprocess.run(
                [sys.executable, '-B', '-c', script, str(scripts), str(ROOT)],
                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=60,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            return json.loads(completed.stdout)

        scripts_relative = 'skills/math-logic-mindmap/scripts'
        expected = identity(ROOT / scripts_relative)
        with tempfile.TemporaryDirectory() as directory:
            aliases = [ROOT / 'skills' / '..' / scripts_relative]
            if os.name == 'posix':
                link = Path(directory) / 'project'
                link.symlink_to(ROOT, target_is_directory=True)
                aliases.append(link / scripts_relative)
            for scripts in [ROOT / scripts_relative, *aliases]:
                with self.subTest(scripts=str(scripts)):
                    actual = identity(scripts)
                    self.assertIn(scripts_relative + '/math_logic_mindmap/bundle.py', actual['files'])
                    for key in actual['files']:
                        self.assertFalse(Path(key).is_absolute())
                        self.assertNotIn('..', Path(key).parts)
                        self.assertFalse(key.startswith('math_logic_mindmap/'))
                    self.assertEqual(actual, expected)

    def backups(self):
        parent = self.root / '.build/backups' / self.slug
        return sorted(p for p in parent.iterdir() if p.is_dir()) if parent.exists() else []

    def record_visual_pass(self):
        state = bundle.status(self.root, self.slug)
        evidence = {'actor': 'user', 'reviewer': 'SYNTHETIC TEST ONLY',
                    'environment': {'obsidian': 'test', 'advanced_canvas': 'test', 'theme': 'test'},
                    'artifact_hashes': state['artifact_hashes'], 'presentation_hash': state['presentation_hash'],
                    'checks': {key: {'status': 'PASS', 'evidence': 'Synthetic isolated test'}
                               for key in bundle.VISUAL_CHECKS}}
        path = self.proof_dir / 'canonical-smoke.visual-review.json'
        write_json(path, evidence)
        bundle.record_review(self.root, self.slug, path)

    def test_release_and_repeat(self):
        first = self.publish()
        self.assertEqual(first['visual'], 'UNREVIEWED')
        self.assertEqual(first['change_kind'], 'artifacts')
        self.assertFalse(first['backup_created'])
        self.assertIsNone(first['backup'])
        self.assertIsNone(first['retained_backup'])
        manifest = read_json(self.proof_dir / 'canonical-smoke.manifest.json')
        self.assertNotIn('canvas_snapshot', manifest)
        self.assertIn('canvas_semantic', manifest)
        self.assertIn('canvas_persisted_hash', manifest)
        self.assertTrue((self.root / '.build/staging/canonical-smoke').is_dir())
        self.record_visual_pass()
        before = bundle.status(self.root, self.slug)['artifact_hashes']
        manifest_before = (self.proof_dir / 'canonical-smoke.manifest.json').read_bytes()
        repeated = self.publish()
        self.assertEqual(repeated['change_kind'], 'none')
        self.assertEqual(repeated['visual'], 'PASS')
        self.assertFalse(repeated['backup_created'])
        self.assertEqual(manifest_before, (self.proof_dir / 'canonical-smoke.manifest.json').read_bytes())
        self.assertEqual(before, bundle.status(self.root, self.slug)['artifact_hashes'])
        self.assertEqual(self.backups(), [])
        self.assertEqual(bundle.validate_bundle(self.root, self.model)['machine'], 'PASS')

    def test_invalid_models(self):
        mutations = [
            lambda m: m['nodes'].append(copy.deepcopy(m['nodes'][0])),
            lambda m: m['nodes'][0].update(title='长' * 50),
            lambda m: m['edges'][0].update(target='MISSING'),
            lambda m: m['edges'][0].update(label_text='[[不可点击]]'),
            lambda m: m.update(slug='../escape'),
        ]
        for mutate in mutations:
            m = copy.deepcopy(self.model)
            mutate(m)
            with self.subTest(mutation=mutate), self.assertRaises((Invalid, ValueError)):
                validate(m)

    def test_failed_build_preserves_diagnostics_without_identity(self):
        with patch('math_logic_mindmap.bundle.validate_bundle', side_effect=Invalid('test gate rejection')):
            with self.assertRaisesRegex(Invalid, 'test gate rejection'):
                bundle.build(self.root, self.path)
        folders=list((self.root/'.build/work').iterdir())
        self.assertEqual(len(folders),1)
        work=folders[0]
        self.assertTrue((work/'reports/routing.json').exists())
        self.assertTrue((work/'reports/diagnostics.json').exists())
        self.assertEqual(read_json(work/'failure.json')['status'],'BLOCKED')
        self.assertFalse((work/'build.json').exists())
        self.assertFalse((self.root/'.build/staging'/self.slug).exists())

    def test_build_reports_do_not_embed_full_reports(self):
        bundle.build(self.root, self.path, layout_report=True)
        stage = self.root / '.build/staging/canonical-smoke'
        build = read_json(stage / 'build.json')
        layout_report = read_json(stage / 'layout-report.json')
        diagnostics = read_json(stage / 'reports/diagnostics.json')
        self.assertNotIn('report', build)
        self.assertNotIn('routing', layout_report)
        self.assertEqual(layout_report['routing_report'], 'reports/routing.json')
        self.assertEqual(layout_report['diagnostics_report'], 'reports/diagnostics.json')
        self.assertIn('layout_metrics', layout_report)
        for key in ('coordinate_metrics', 'abstract_estimates', 'route_metrics', 'measurement_note'):
            self.assertNotIn(key, layout_report)
        for key in ('endpoint_manhattan_total', 'crowded_inputs', 'route_conflict_counts', 'route_clearance_counts'):
            self.assertNotIn(key, layout_report['layout_metrics'])
        self.assertNotIn('paths', diagnostics)

    def test_merge_advisory_survives_build_and_release_without_blocking(self):
        model = read_json(ROOT / 'tests/fixtures/feature-coverage.proof.json')
        slug = model['slug']
        path = self.root / 'proof' / slug / f'{slug}.proof.json'
        write_json(path, model)
        result = bundle.build(self.root, path)
        review_warning = next(w for w in result['warnings'] if w.startswith('GRANULARITY-REVIEW:'))
        self.assertIn('D1,D2,D3', review_warning)
        stage = self.root / '.build/staging' / slug
        report = read_json(stage / 'reports/granularity.json')
        self.assertEqual([a['nodes'][1] for a in report['advisories'] if not a['reviewed']],
                         ['D1', 'D2', 'D3'])
        self.assertFalse(report['unresolved'])
        self.assertEqual(read_json(stage / 'build.json')['machine']['warnings'], result['warnings'])
        released = bundle.release(self.root, slug)
        self.assertEqual(released['machine'], 'PASS')
        self.assertEqual(released['warnings'], [review_warning])
        manifest = read_json(self.root / 'proof' / slug / f'{slug}.manifest.json')
        self.assertIn(review_warning, manifest['machine']['warnings'])

    def test_canvas_schema_allows_host_extension_fields(self):
        canvas = bundle.layout(self.model, validate(self.model))
        canvas['metadata']['hostExtension'] = {'keep': True}
        canvas['nodes'][0]['hostExtension'] = {'keep': True}
        canvas['edges'][0]['hostExtension'] = {'keep': True}
        canvas['edges'][0]['proofRoute']['hostExtension'] = {'keep': True}
        self.assertIsInstance(bundle.check_canvas(self.model, canvas, validate(self.model)), list)
        canvas['edges'][0]['proofRoute']['midOffset'] = float('inf')
        with self.assertRaisesRegex(Invalid, 'finite number'):
            bundle.check_canvas(self.model, canvas, validate(self.model))

    def test_unsupported_geometry_field_is_rejected(self):
        c=bundle.layout(self.model,validate(self.model))
        c['edges'][0]['proofGeometry']={'profile':'unsupported'}
        with self.assertRaisesRegex(Invalid,'CANVAS-SCHEMA'):
            bundle.check_canvas(self.model,c,validate(self.model))

    def test_release_without_math_or_runtime_review(self):
        bundle.build(self.root, self.path)
        self.assertFalse((self.proof_dir / 'canonical-smoke.math-review.json').exists())
        self.assertFalse((self.proof_dir / 'canonical-smoke.runtime-review.json').exists())
        self.assertEqual(bundle.release(self.root, self.slug)['machine'], 'PASS')
        manifest = read_json(self.proof_dir / 'canonical-smoke.manifest.json')
        self.assertNotIn('runtime_review', manifest)
        self.assertEqual(status_report(self.root, self.slug)['mathematical_review'], 'UNREVIEWED')

    def test_artifact_backups_track_content_versions(self):
        first = self.publish()
        self.assertFalse(first['backup_created'])
        changed = copy.deepcopy(self.model)
        changed['context']['背景'] += ' B 版本。'
        write_json(self.path, changed)
        second = self.publish()
        self.assertEqual(second['change_kind'], 'artifacts')
        self.assertTrue(second['backup_created'])
        backup_a = self.backups()
        self.assertEqual(len(backup_a), 1)
        self.assertEqual(read_json(backup_a[0] / 'manifest.json')['model_hash'], model_identity(self.model))

        repeated = self.publish()
        self.assertEqual(repeated['change_kind'], 'none')
        self.assertEqual(self.backups(), backup_a)
        self.assertEqual(repeated['retained_backup'], backup_a[0].relative_to(self.root).as_posix())

        third = copy.deepcopy(changed)
        third['context']['背景'] += ' C 版本。'
        write_json(self.path, third)
        released = self.publish()
        backup_b = self.backups()
        self.assertEqual(released['change_kind'], 'artifacts')
        self.assertEqual(len(backup_b), 1)
        self.assertNotEqual(backup_a[0].name, backup_b[0].name)
        self.assertEqual(read_json(backup_b[0] / 'manifest.json')['model_hash'], model_identity(changed))

    def test_presentation_only_release_resets_visual_without_rotating_backup(self):
        self.publish()
        changed = copy.deepcopy(self.model)
        changed['context']['背景'] += ' B 版本。'
        write_json(self.path, changed)
        self.publish()
        retained = self.backups()
        self.record_visual_pass()
        write_text(self.root / '.obsidian/snippets/math-logic-mindmap.css', '/* presentation change */')
        result = self.publish()
        self.assertEqual(result['change_kind'], 'metadata')
        self.assertFalse(result['backup_created'])
        self.assertEqual(self.backups(), retained)
        self.assertEqual(bundle.status(self.root, self.slug)['visual'], 'UNREVIEWED')

    def test_math_review_only_release_preserves_visual_and_backup(self):
        self.publish()
        changed = copy.deepcopy(self.model)
        changed['context']['背景'] += ' B 版本。'
        write_json(self.path, changed)
        self.publish()
        retained = self.backups()
        self.record_visual_pass()
        review = {'model_hash': model_identity(changed), 'status': 'PASS',
                  'reviewer': 'SYNTHETIC TEST ONLY', 'summary': 'Synthetic isolated mathematical review'}
        write_json(self.proof_dir / 'canonical-smoke.math-review.json', review)
        result = self.publish()
        self.assertEqual(result['change_kind'], 'metadata')
        self.assertEqual(self.backups(), retained)
        self.assertEqual(bundle.status(self.root, self.slug)['visual'], 'PASS')

    def test_metadata_write_failure_restores_manifest_and_checklist(self):
        self.publish()
        manifest_path = self.proof_dir / 'canonical-smoke.manifest.json'
        checklist_path = self.root / 'note/canonical-smoke/_review-checklist.md'
        manifest_before = manifest_path.read_bytes()
        checklist_before = checklist_path.read_bytes()
        write_text(self.root / '.obsidian/snippets/math-logic-mindmap.css', '/* presentation change */')
        bundle.build(self.root, self.path)

        def fail_write(path, manifest):
            write_json(path.with_name(path.name + '.math-logic-mindmap-tmp'), manifest)
            raise OSError('injected metadata write failure')

        with patch.object(bundle, '_write_manifest_atomic', side_effect=fail_write), self.assertRaises(OSError):
            bundle.release(self.root, self.slug)
        self.assertEqual(manifest_path.read_bytes(), manifest_before)
        self.assertEqual(checklist_path.read_bytes(), checklist_before)
        self.assertFalse(any(self.root.rglob('*.math-logic-mindmap-tmp')))
        self.assertEqual(self.backups(), [])

    def test_status_reports_mathematical_review_lifecycle(self):
        review = {
            'model_hash': model_identity(self.model),
            'status': 'PASS',
            'reviewer': 'SYNTHETIC TEST ONLY',
            'summary': 'Synthetic isolated mathematical review',
        }
        write_json(self.proof_dir / 'canonical-smoke.math-review.json', review)
        self.publish()
        self.assertEqual(status_report(self.root, self.slug)['mathematical_review'], 'PASS')

        write_text(self.root / '.obsidian/snippets/math-logic-mindmap.css', '/* visual-only change */')
        visual_stale = status_report(self.root, self.slug)
        self.assertEqual(visual_stale['visual'], 'STALE')
        self.assertEqual(visual_stale['mathematical_review'], 'PASS')

        changed = copy.deepcopy(self.model)
        changed['context']['背景'] += ' 测试模型变化。'
        write_json(self.path, changed)
        self.assertEqual(status_report(self.root, self.slug)['mathematical_review'], 'STALE')

    def test_semantic_contract_failures(self):
        cases = ['combine_inputs', 'combine_output', 'transform_input', 'reference', 'intuition', 'root', 'status', 'structural_label', 'symbols']
        for case in cases:
            m = copy.deepcopy(self.model)
            combine = next(n for n in m['nodes'] if n['type'] == 'COMBINE')
            transform = next(n for n in m['nodes'] if n['type'] == 'TRANSFORM')
            if case == 'combine_inputs':
                combine['combine_inputs'].pop()
            elif case == 'combine_output':
                combine['combine_output_latex'] = '0=1'
            elif case == 'transform_input':
                transform['transform_input'] = 'A1'
            elif case == 'reference':
                m['edges'][0]['display_mode'] = 'REFERENCE'
            elif case == 'intuition':
                m['nodes'][0]['type'] = 'INTUITION'
            elif case == 'root':
                m['nodes'][0]['type'] = 'DERIVATION'
            elif case == 'status':
                m['theorem']['status'] = 'refuted'
            elif case == 'structural_label':
                next(e for e in m['edges'] if e['detail_mode'] == 'STRUCTURAL_ONLY')['label_text'] = '多余解释'
            else:
                next(b for b in combine['derivation'] if b['kind'] == 'formula')['symbols'] = []
            with self.subTest(case=case), self.assertRaises(Invalid):
                validate(m)

    def test_math_markdown_and_json(self):
        from math_logic_mindmap.common import table_cell
        self.assertEqual(table_cell('a|b'), r'a\|b')
        m = copy.deepcopy(self.model)
        validate(m)
        write_json(self.path, m)
        self.assertEqual(read_json(self.path), m)
        self.assertNotIn(b'\r\n', self.path.read_bytes())
        self.assertFalse(self.path.read_bytes().startswith(b'\xef\xbb\xbf'))

    def test_markdown_assumptions_render_in_notes_and_canvas(self):
        notes = generate_notes(self.model)
        index = notes['note/canonical-smoke/index.md']
        self.assertIn(r'- $u\le v$', index)
        self.assertIn(r'- $c>0$', index)
        canvas = bundle.layout(self.model, validate(self.model))
        header = next(node['text'] for node in canvas['nodes'] if node['id'] == 'UIHeader')
        self.assertIn(r'- $u\le v$', header)
        self.assertIn(r'- $c>0$', header)
        self.assertNotIn(r'- u\le v', index + header)

    def test_symbol_rows_are_atomic_without_rejecting_inner_commas(self):
        for symbol in (
            r'x_{i,j}', r'P(A\mid B)', r'\lambda_i',
            r'\langle u,v\rangle', r'\left\langle u,v\right\rangle',
            r'\lfloor a,b\rfloor', r'\lceil a,b\rceil',
            r'\lvert a,b\rvert', r'\lVert a,b\rVert',
            r'\langle x_{i,j},P(A\mid B)\rangle',
        ):
            with self.subTest(symbol=symbol):
                self.assertFalse(_has_top_level_symbol_separator(symbol))
        for symbol in (
            'I,f,n', r'\lambda_1,\dots,\lambda_n', r'I\quad f',
            r'\langle u,v\rangle,w',
        ):
            with self.subTest(symbol=symbol):
                self.assertTrue(_has_top_level_symbol_separator(symbol))

        for symbol in ('I,f,n', r'\lambda_1,\dots,\lambda_n', r'I\quad f'):
            model = copy.deepcopy(self.model)
            model['symbols'][0]['symbol_latex'] = symbol
            with self.subTest(validation=symbol), self.assertRaisesRegex(Invalid, 'SYMBOL-ROW-ATOMIC'):
                validate(model)

    def test_symbol_ownership_and_width_are_warnings(self):
        warnings = []
        row = {
            'symbol_latex': r'\left\lVert unrelated\right\rVert_{L^2(\Omega)}',
            'definition_role': '测试长记号',
            'range_unit': '不适用',
            'interpretation': '仅用于风险测试',
        }
        _check_symbol_rows([row], warnings=warnings, location='test', latex='x')
        self.assertTrue(any('SYMBOL-OWNERSHIP-RISK' in warning for warning in warnings))
        self.assertTrue(any('SYMBOL-WIDTH-RISK' in warning for warning in warnings))

    def test_fixture_symbol_rows_and_combine_chain_order(self):
        model = read_json(ROOT / 'tests/fixtures/canonical-smoke.proof.json')
        validate(model)
        nodes = {node['id']: node for node in model['nodes']}

        def formulas(value):
            if isinstance(value, dict):
                if value.get('kind') == 'formula':
                    yield value
                for child in value.values():
                    yield from formulas(child)
            elif isinstance(value, list):
                for child in value:
                    yield from formulas(child)

        for block in formulas(model):
            for row in block['symbols']:
                self.assertFalse(_has_top_level_symbol_separator(row['symbol_latex']))

        c1 = nodes['C1']
        a1 = next(b for s in nodes['A1']['sections'] for b in s['blocks'] if b['kind'] == 'formula')
        c1_source = next(b for b in c1['derivation'] if b['id'] == 'input1')
        self.assertEqual(c1_source['symbols'], a1['symbols'])
        self.assertEqual(
            [row['symbol_latex'] for row in c1['derivation_chain']['symbols']],
            ['u', 'v', 'c'],
        )
        note = generate_notes(model)[f'note/{model["slug"]}/C1.md']
        self.assertNotIn('a,b', note)

    def test_stage_tamper(self):
        bundle.build(self.root, self.path)
        p = self.root / '.build/staging/canonical-smoke/note/canonical-smoke/A1.md'
        p.write_text('tampered', encoding='utf-8')
        with self.assertRaises(Invalid):
            bundle.release(self.root, self.slug)

    def test_personal_preserved_managed_protected(self):
        self.publish()
        p = self.root / 'note/canonical-smoke/A1.md'
        write_text(p, p.read_text(encoding='utf-8').replace(PERSONAL_END, '自己的理解。\n' + PERSONAL_END))
        self.publish()
        self.assertIn('自己的理解。', p.read_text(encoding='utf-8'))
        write_text(p, '手动改动\n' + p.read_text(encoding='utf-8'))
        with self.assertRaises(Invalid):
            self.publish()

    def test_layout_round_trip(self):
        self.publish()
        p = self.root / 'mindmap/canonical-smoke.canvas'
        c = read_json(p)
        for n in c['nodes']:
            n['x'] += 123
            n['userExtension'] = {'keep': True}
        write_json(p, c)
        bundle.import_layout(self.root, self.slug)
        saved = read_json(self.proof_dir / 'canonical-smoke.layout.json')
        self.assertNotIn('profile', saved)
        self.assertNotIn('edges', saved)
        self.publish()
        actual = read_json(p)
        self.assertEqual({n['id']: n['x'] for n in c['nodes']}, {n['id']: n['x'] for n in actual['nodes']})
        self.assertTrue(all(n['userExtension']['keep'] for n in actual['nodes']))

    def test_integral_route_offsets_survive_obsidian_number_normalization(self):
        self.publish()
        p = self.root / 'mindmap/canonical-smoke.canvas'
        canvas = read_json(p)
        for edge in canvas['edges']:
            for key, value in edge.get('proofRoute', {}).items():
                if key.endswith('Offset') and isinstance(value, float) and value.is_integer():
                    edge['proofRoute'][key] = int(value)
        write_json(p, canvas)
        self.assertEqual(bundle.status(self.root, self.slug)['machine'], 'PASS')
        next(node for node in canvas['nodes'] if node['type'] != 'group')['x'] += 1
        write_json(p, canvas)
        self.assertEqual(bundle.status(self.root, self.slug)['machine'], 'STALE')

    def test_canvas_json_formatting_preserves_status_and_review(self):
        self.publish()
        path = self.root / 'mindmap/canonical-smoke.canvas'
        canvas = read_json(path)
        path.write_text(json.dumps(canvas, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
        self.assertEqual(bundle.status(self.root, self.slug)['machine'], 'PASS')
        self.record_visual_pass()
        self.assertEqual(bundle.status(self.root, self.slug)['visual'], 'PASS')
        canvas['nodes'][0]['x'] += 1
        write_json(path, canvas)
        self.assertEqual(bundle.status(self.root, self.slug)['machine'], 'STALE')

    def test_content_import_rejected(self):
        self.publish()
        p = self.root / 'mindmap/canonical-smoke.canvas'
        c = read_json(p)
        next(n for n in c['nodes'] if n.get('text'))['text'] += '伪造'
        write_json(p, c)
        with self.assertRaises(Invalid):
            bundle.import_layout(self.root, self.slug)

    def test_missing_note_and_collision(self):
        self.publish()
        p = self.root / 'mindmap/canonical-smoke.canvas'
        c = read_json(p)
        cards = [n for n in c['nodes'] if n['type'] == 'text' and n['id'] != 'UIHeader']
        cards[1].update(x=cards[0]['x'], y=cards[0]['y'])
        write_json(p, c)
        with self.assertRaises(Invalid):
            bundle.validate_bundle(self.root, self.model)

    def test_review_binding_and_staleness(self):
        self.publish()
        s = bundle.status(self.root, self.slug)
        e = {'actor': 'user', 'reviewer': 'SYNTHETIC TEST ONLY',
             'environment': {'obsidian': 'test', 'advanced_canvas': 'test', 'theme': 'test'},
             'artifact_hashes': s['artifact_hashes'], 'presentation_hash': s['presentation_hash'],
             'checks': {k: {'status': 'PASS', 'evidence': 'Synthetic isolated test'} for k in bundle.VISUAL_CHECKS}}
        p = self.proof_dir / 'canonical-smoke.visual-review.json'
        write_json(p, e)
        self.assertEqual(bundle.record_review(self.root, self.slug, p)['visual'], 'PASS')
        self.assertEqual(bundle.status(self.root, self.slug)['visual'], 'PASS')
        write_text(self.root / '.obsidian/snippets/math-logic-mindmap.css', '/* changed */')
        self.assertEqual(bundle.status(self.root, self.slug)['visual'], 'STALE')
        with self.assertRaises(Invalid):
            bundle.record_review(self.root, self.slug, p)

    def test_model_outside_topic_directory_is_rejected(self):
        external_path = self.root / 'drafts' / f'{self.slug}.proof.json'
        write_json(external_path, self.model)
        with self.assertRaisesRegex(Invalid, 'PROOF-PATH'):
            bundle.build(self.root, external_path)

    def test_noncanonical_staging_source_is_rejected(self):
        bundle.build(self.root, self.path)
        meta_path = self.root / '.build/staging/canonical-smoke/build.json'
        meta = read_json(meta_path)
        meta['source'] = f'drafts/{self.slug}.proof.json'
        write_json(meta_path, meta)
        with self.assertRaisesRegex(Invalid, 'PROOF-PATH'):
            bundle.release(self.root, self.slug)

    def test_noncanonical_manifest_source_is_rejected_by_consumers(self):
        self.publish()
        manifest_path = self.proof_dir / 'canonical-smoke.manifest.json'
        manifest = read_json(manifest_path)
        manifest['source'] = f'drafts/{self.slug}.proof.json'
        write_json(manifest_path, manifest)
        consumers = (
            lambda: bundle.status(self.root, self.slug),
            lambda: status_report(self.root, self.slug),
            lambda: bundle.import_layout(self.root, self.slug),
            lambda: bundle.record_review(self.root, self.slug, self.proof_dir / 'missing-review.json'),
        )
        for consume in consumers:
            with self.subTest(consumer=consume), self.assertRaisesRegex(Invalid, 'PROOF-PATH'):
                consume()

    def test_release_rollback(self):
        self.publish()
        before = bundle.status(self.root, self.slug)['artifact_hashes']
        changed = copy.deepcopy(self.model)
        changed['context']['背景'] += ' artifact rollback test.'
        write_json(self.path, changed)
        bundle.build(self.root, self.path)
        original = bundle.validate_bundle
        def fail_final(root, model, config=None):
            if Path(root) == self.root:
                raise Invalid('injected final verification failure')
            return original(root, model, config)
        with patch.object(bundle, 'validate_bundle', side_effect=fail_final), self.assertRaises(Invalid):
            bundle.release(self.root, self.slug)
        self.assertEqual(before, bundle.status(self.root, self.slug)['artifact_hashes'])

    def test_entry_sync_and_canonical_plugin(self):
        self.assertEqual(sync_skills(ROOT, check=True)['skill_sync'], 'PASS')
        manifest = read_json(ROOT/'plugins/proof-routing/manifest.json')
        self.assertEqual(manifest['id'], 'proof-routing')
        self.assertEqual(manifest['version'], '0.6.1')
        for name in ('manifest.json', 'main.js', 'geometry-core.cjs'):
            self.assertEqual((ROOT/'plugins/proof-routing'/name).read_bytes(),
                             (ROOT/'.obsidian/plugins/proof-routing'/name).read_bytes())
        setup = (ROOT/'docs/obsidian-setup.md').read_text(encoding='utf-8')
        self.assertIn('readable source is `plugins/proof-routing/`', setup)
        self.assertIn('--confirm proof-routing', setup)

    def test_release_rejects_a_partial_managed_plugin_before_writing(self):
        bundle.build(self.root, self.path)
        for name in ('manifest.json', 'main.js', 'geometry-core.cjs'):
            source = self.root / 'plugins/proof-routing' / name
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes((ROOT / 'plugins/proof-routing' / name).read_bytes())
        installed = self.root / '.obsidian/plugins/proof-routing/manifest.json'
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_bytes((self.root / 'plugins/proof-routing/manifest.json').read_bytes())
        before = {p.relative_to(self.root).as_posix(): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(Invalid, 'PROOF-ROUTING-SYNC'):
            bundle.release(self.root, self.slug)
        after = {p.relative_to(self.root).as_posix(): p.read_bytes()
                 for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
