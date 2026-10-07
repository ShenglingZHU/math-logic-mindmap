"""Full-model checks for case pairs, nested scopes, and published artifacts."""
import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/math-logic-mindmap/scripts'))

from math_logic_mindmap import bundle
from math_logic_mindmap.common import Invalid, read_json, write_json
from math_logic_mindmap.model import validate


class ScopeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.model = read_json(ROOT / 'tests/fixtures/case-nested-smoke.proof.json')

    def test_case_nested_scope_and_intuition_publish(self):
        validate(self.model)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            slug = self.model['slug']
            proof = root / 'proof' / slug / f'{slug}.proof.json'
            write_json(proof, self.model)
            self.assertEqual(bundle.build(root, proof)['machine'], 'PASS')
            self.assertEqual(bundle.release(root, slug)['machine'], 'PASS')
            canvas = read_json(root / 'mindmap' / f'{slug}.canvas')
            nodes = {node['id']: node for node in canvas['nodes']}
            self.assertEqual(nodes['K1']['styleAttributes']['shape'], 'circle')
            self.assertIn('GOuter', nodes)
            self.assertIn('GInner', nodes)
            outer, inner = nodes['GOuter'], nodes['GInner']
            self.assertLessEqual(outer['x'], inner['x'])
            self.assertLessEqual(outer['y'], inner['y'])
            self.assertGreaterEqual(outer['x'] + outer['width'], inner['x'] + inner['width'])
            self.assertGreaterEqual(outer['y'] + outer['height'], inner['y'] + inner['height'])
            self.assertIn('U1', nodes)
            note = (root / 'note' / slug / 'C1.md').read_text(encoding='utf-8')
            self.assertIn('EKD1', note)
            self.assertIn('EKD2', note)
            self.assertEqual(bundle.status(root, slug)['machine'], 'PASS')

    def test_nested_reductio_and_conditional_proofs_publish(self):
        for slug in ('nested-quantifier-smoke', 'nested-conditional-smoke'):
            with self.subTest(slug=slug), tempfile.TemporaryDirectory() as directory:
                model = read_json(ROOT / 'tests/fixtures' / f'{slug}.proof.json')
                result = validate(model)
                self.assertFalse([w for w in result['warnings'] if w.startswith('SYMBOL-REFERENCE-RISK')])
                root = Path(directory)
                proof = root / 'proof' / slug / f'{slug}.proof.json'
                write_json(proof, model)
                self.assertEqual(bundle.build(root, proof)['machine'], 'PASS')
                self.assertEqual(bundle.release(root, slug)['machine'], 'PASS')
                self.assertEqual(bundle.status(root, slug)['machine'], 'PASS')
                canvas = read_json(root / 'mindmap' / f'{slug}.canvas')
                self.assertIn('GOuter', {n['id'] for n in canvas['nodes']})
                self.assertIn('GInner', {n['id'] for n in canvas['nodes']})

        wrong_rule = read_json(ROOT / 'tests/fixtures/nested-quantifier-smoke.proof.json')
        next(e for e in wrong_rule['edges'] if e['id'] == 'EXR')['generalizes'] = ['x']
        with self.assertRaisesRegex(Invalid, 'GENERALIZATION EXR'):
            validate(wrong_rule)
        leak = read_json(ROOT / 'tests/fixtures/nested-quantifier-smoke.proof.json')
        next(n for n in leak['nodes'] if n['id'] == 'T1')['uses_symbols'] = ['x']
        with self.assertRaisesRegex(Invalid, 'SYMBOL-LEAK T1'):
            validate(leak)

    def test_exact_case_and_discharge_diagnostics(self):
        count = copy.deepcopy(self.model)
        next(n for n in count['nodes'] if n['id'] == 'K1')['case_branches'].pop()
        with self.assertRaisesRegex(Invalid, 'CASE K1: input or branch count is invalid'):
            validate(count)

        pair = copy.deepcopy(self.model)
        next(n for n in pair['nodes'] if n['id'] == 'C1').pop('paired_case')
        with self.assertRaisesRegex(Invalid, 'CASE K1: requires one paired'):
            validate(pair)

        contradiction = copy.deepcopy(self.model)
        next(n for n in contradiction['nodes'] if n['id'] == 'X1')['type'] = 'DERIVATION'
        with self.assertRaisesRegex(Invalid, 'DISCHARGES EX1R1: contradiction source required'):
            validate(contradiction)

        contextual = copy.deepcopy(self.model)
        contextual['scopes'][1]['opening_edge'] = 'ED1H2'
        edge = copy.deepcopy(next(e for e in contextual['edges'] if e['id'] == 'ED1CI'))
        edge.update(id='ED1H2', target='H2', relation='OPENS_SCOPE')
        contextual['edges'].append(edge)
        with self.assertRaisesRegex(Invalid, 'SCOPE-OPEN Inner'):
            validate(contextual)

    def test_witness_rule_failures_reach_full_validator(self):
        model = copy.deepcopy(self.model)
        nodes = {n['id']: n for n in model['nodes']}
        intro = nodes['H2']
        intro.update(type='LOCAL_INTRODUCTION', scope='Outer', introduction_mode='arbitrary',
                     bindings=[{'id': 'c', 'symbol_latex': 'c', 'domain_latex': 'X', 'depends_on': []}])
        intro['formula_latex'] = 'X'
        intro['sections'][0]['blocks'][0]['latex'] = 'X'
        result = copy.deepcopy(nodes['D1'])
        result.update(id='R2', scope='Inner', title='局部数据的结果',
                      formula_latex='\\neg(P\\lor\\neg P)', branch_condition_latex=None,
                      uses_symbols=['c'])
        result['sections'] = copy.deepcopy(intro['sections'])
        result['sections'][0]['blocks'][0]['latex'] = result['formula_latex']
        model['nodes'].append(result)
        model['scopes'][1]['opening_edge'] = 'EH2R2'
        for edge in model['edges']:
            if edge['id'] == 'EH2CI':
                edge.update(id='ER2CI', source='R2')
            elif edge['id'] == 'EX1R1':
                edge.update(discharge_rule='universal_generalization', discharges=[],
                            generalizes=['c'])
        feed = copy.deepcopy(next(e for e in model['edges'] if e['id'] == 'EKD1'))
        feed.update(id='ED1H2', source='D1', target='H2', relation='REQUIRED_FOR')
        feed.pop('case_condition_latex', None)
        model['edges'].append(feed)
        opening = copy.deepcopy(next(e for e in model['edges'] if e['id'] == 'ED1CI'))
        opening.update(id='EH2R2', source='H2', target='R2', relation='OPENS_SCOPE')
        model['edges'].append(opening)
        operation = nodes['CI']
        operation['combine_inputs'] = ['D1', 'R2']
        for key in ('input_review', 'input_usage'):
            for row in operation[key]:
                if row['node'] == 'H2':
                    row['node'] = 'R2'
        for row in operation['derivation_chain']['rows']:
            if row['kind'] == 'apply':
                row['source']['node'] = 'R2'
        intro['input_context'] = []
        result['input_context'] = [{'edge_id': 'EH2R2', 'contribution': '在局部作用域内使用该变量。'}]
        result.pop('branch_condition_latex', None)
        model['presentation']['spine'].insert(model['presentation']['spine'].index('CI'), 'R2')
        model['proof_flow'][0]['nodes'].append('R2')
        validate(model)

        reserved = copy.deepcopy(model)
        global_symbol = copy.deepcopy(reserved['symbols'][0])
        global_symbol['symbol_latex'] = 'c'
        reserved['symbols'].append(global_symbol)
        with self.assertRaisesRegex(Invalid, 'BINDING-FRESH c'):
            validate(reserved)

        witness = copy.deepcopy(model)
        next(n for n in witness['nodes'] if n['id'] == 'H2')['introduction_mode'] = 'witness'
        with self.assertRaisesRegex(Invalid, 'WITNESS-CLOSE EX1R1'):
            validate(witness)
        next(e for e in witness['edges'] if e['id'] == 'EX1R1')['discharge_rule'] = 'existential_elimination'
        with self.assertRaisesRegex(Invalid, 'GENERALIZATION EX1R1'):
            validate(witness)


if __name__ == '__main__':
    unittest.main()
