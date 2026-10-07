"""Neutral structural regressions for lexical scope and case semantics."""
import copy
import sys
import unittest
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/math-logic-mindmap/scripts'))
from math_logic_mindmap.common import Invalid
from math_logic_mindmap.scope_semantics import quantifier_dependencies, validate_scopes
from math_logic_mindmap.model import estimate, node_color_role
from math_logic_mindmap.render import card


def node(nid, typ='DERIVATION', scope=None, **extra):
    return {'id': nid, 'type': typ, 'title': nid, 'scope': scope, 'uses_symbols': [], **extra}


def edge(eid, source, target, relation='REQUIRED_FOR', detail='EDGE_DETAIL', **extra):
    return {'id': eid, 'source': source, 'target': target, 'relation': relation,
            'detail_mode': detail, 'uses_symbols': [], **extra}


def check(model):
    model.setdefault('symbols', [])
    nodes = {n['id']: n for n in model['nodes']}
    incoming, outgoing = defaultdict(list), defaultdict(list)
    for e in model['edges']:
        incoming[e['target']].append(e['source'])
        outgoing[e['source']].append(e['target'])
    degrees = {nid: len(incoming[nid]) for nid in nodes}
    todo = deque(nid for nid in nodes if not degrees[nid])
    order = []
    while todo:
        nid = todo.popleft()
        order.append(nid)
        for child in outgoing[nid]:
            degrees[child] -= 1
            if not degrees[child]:
                todo.append(child)
    assert len(order) == len(nodes)
    warnings = []
    validate_scopes(model, nodes, incoming, outgoing, order, warnings)
    return warnings


class ScopeSemanticsTests(unittest.TestCase):
    def test_arbitrary_context_reaches_nested_assumption_and_closes_in_two_steps(self):
        model = {'symbols': [], 'scopes': [
            {'id': 'Outer', 'title': 'Outer', 'kind': 'local', 'opened_by': 'I',
             'opening_edge': 'E2', 'closed_by': 'E7'},
            {'id': 'Inner', 'title': 'Inner', 'kind': 'local', 'parent_scope': 'Outer',
             'opened_by': 'H', 'closed_by': 'E5'}],
            'nodes': [node('A', 'DEFINITION'),
                      node('I', 'LOCAL_INTRODUCTION', introduction_mode='arbitrary',
                           bindings=[{'id': 'x', 'symbol_latex': 'x', 'domain_latex': 'X', 'depends_on': []}]),
                      node('F', scope='Outer', uses_symbols=['x']),
                      node('H', 'HYPOTHESIS_LOCAL', 'Inner', uses_symbols=['x']),
                      node('C', 'CONTRADICTION', 'Inner', uses_symbols=['x']),
                      node('R', scope='Outer', uses_symbols=['x']),
                      node('J', 'COMBINE', 'Outer', uses_symbols=['x']), node('T', 'TARGET')],
            'edges': [edge('E1', 'A', 'I'), edge('E2', 'I', 'F', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'),
                      edge('E3', 'F', 'J'), edge('E4', 'H', 'C'),
                      edge('E5', 'C', 'R', 'DISCHARGES', closes_scope='Inner',
                           discharge_rule='reductio', discharges=['H'], generalizes=[], uses_symbols=['x']),
                      edge('E6', 'R', 'J'),
                      edge('E7', 'J', 'T', 'DISCHARGES', closes_scope='Outer',
                           discharge_rule='universal_generalization', discharges=[],
                           generalizes=['x'], uses_symbols=['x'])]}
        check(model)
        conditional = copy.deepcopy(model)
        conditional['edges'][4]['discharge_rule'] = 'conditional_proof'
        check(conditional)

        combined = copy.deepcopy(model)
        combined['edges'][4]['generalizes'] = ['x']
        with self.assertRaisesRegex(Invalid, 'GENERALIZATION E5'):
            check(combined)
        escaped = copy.deepcopy(model)
        escaped['nodes'][-1]['uses_symbols'] = ['x']
        with self.assertRaisesRegex(Invalid, 'SYMBOL-LEAK T'):
            check(escaped)

        late = copy.deepcopy(model)
        late['nodes'].append(node('Q', 'CONSTRUCTION', 'Outer', uses_symbols=['y'], bindings=[
            {'id': 'y', 'symbol_latex': 'y', 'domain_latex': 'Y', 'depends_on': [],
             'definition_latex': 'y=f(x)', 'well_defined': 'defined', 'domain_check': 'in Y'}]))
        late['edges'].append(edge('E8', 'F', 'Q'))
        late['edges'].append(edge('E9', 'Q', 'J'))
        next(n for n in late['nodes'] if n['id'] == 'H')['uses_symbols'].append('y')
        with self.assertRaisesRegex(Invalid, 'SYMBOL-LEAK H'):
            check(late)

        row = {'symbol_latex': 'x', 'definition_role': 'variable', 'range_unit': 'X',
               'interpretation': 'arbitrary object'}
        annotated = copy.deepcopy(model)
        for nid in ('H', 'T'):
            next(n for n in annotated['nodes'] if n['id'] == nid)['sections'] = [
                {'blocks': [{'kind': 'formula', 'latex': 'x', 'symbols': [copy.deepcopy(row)]}]}]
        self.assertEqual([w for w in check(annotated) if w.startswith('SYMBOL-REFERENCE-RISK')],
                         ['SYMBOL-REFERENCE-RISK H/x: local binding spelling lacks binding_ref'])

        dependent = copy.deepcopy(model)
        dependent['nodes'].append(node('Q', 'CONSTRUCTION', 'Inner', uses_symbols=['x', 'y'], bindings=[
            {'id': 'y', 'symbol_latex': 'y', 'domain_latex': 'Y', 'depends_on': ['x'],
             'definition_latex': 'y=f(x)', 'well_defined': 'defined', 'domain_check': 'in Y'}]))
        next(e for e in dependent['edges'] if e['id'] == 'E4')['target'] = 'Q'
        dependent['edges'].append(edge('E8', 'Q', 'C'))
        check(dependent)

    def test_universal_generalization_cannot_discharge_assumption(self):
        model = {'symbols': [], 'scopes': [{'id': 'L', 'title': 'L', 'kind': 'local',
                 'opened_by': 'I', 'opening_edge': 'E2', 'closed_by': 'E4'}],
                 'nodes': [node('A', 'DEFINITION'), node('I', 'LOCAL_INTRODUCTION',
                    introduction_mode='arbitrary', bindings=[{'id': 'x', 'symbol_latex': 'x',
                    'domain_latex': 'X', 'depends_on': []}]),
                    node('H', 'HYPOTHESIS_LOCAL', 'L', uses_symbols=['x']),
                    node('C', 'CONTRADICTION', 'L', uses_symbols=['x']), node('T', 'TARGET')],
                 'edges': [edge('E1', 'A', 'I'), edge('E2', 'I', 'H', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'),
                           edge('E3', 'H', 'C'), edge('E4', 'C', 'T', 'DISCHARGES', closes_scope='L',
                                discharge_rule='universal_generalization', discharges=['H'],
                                generalizes=['x'], uses_symbols=['x'])]}
        with self.assertRaisesRegex(Invalid, 'DISCHARGES E4: universal generalization cannot discharge a hypothesis'):
            check(model)

    def test_nested_hypothesis_roots_and_contextual_edge_rejection(self):
        model = {'symbols': [], 'scopes': [
            {'id': 'Outer', 'title': 'Outer', 'kind': 'local', 'opened_by': 'H0', 'closed_by': 'E5'},
            {'id': 'Inner', 'title': 'Inner', 'kind': 'local', 'parent_scope': 'Outer',
             'opened_by': 'H1', 'closed_by': 'E2'}],
            'nodes': [node('H0', 'HYPOTHESIS_LOCAL', 'Outer'),
                      node('H1', 'HYPOTHESIS_LOCAL', 'Inner'), node('D1', scope='Inner'),
                      node('D2', scope='Outer'), node('C', 'COMBINE', 'Outer'), node('T', 'TARGET')],
            'edges': [edge('E1', 'H1', 'D1'),
                      edge('E2', 'D1', 'D2', 'DISCHARGES', closes_scope='Inner',
                           discharge_rule='conditional_proof', discharges=['H1'], generalizes=[]),
                      edge('E3', 'H0', 'C'), edge('E4', 'D2', 'C'),
                      edge('E5', 'C', 'T', 'DISCHARGES', closes_scope='Outer',
                           discharge_rule='conditional_proof', discharges=['H0'], generalizes=[])]}
        check(model)
        linked = copy.deepcopy(model)
        linked['edges'].append(edge('E6', 'H0', 'H1', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'))
        linked['scopes'][1]['opening_edge'] = 'E6'
        with self.assertRaisesRegex(Invalid, 'SCOPE-OPEN Inner'):
            check(linked)

    def test_witness_and_fixed_data_cannot_be_generalized(self):
        model = {'symbols': [], 'scopes': [{'id': 'L', 'title': 'L', 'kind': 'local',
                 'opened_by': 'I', 'opening_edge': 'E2', 'closed_by': 'E3'}],
                 'nodes': [node('A', 'KNOWN_RESULT'),
                           node('I', 'LOCAL_INTRODUCTION', introduction_mode='witness',
                                bindings=[{'id': 'c', 'symbol_latex': 'c', 'domain_latex': 'X', 'depends_on': []}]),
                           node('R', scope='L', uses_symbols=['c']), node('T', 'TARGET')],
                 'edges': [edge('E1', 'A', 'I'), edge('E2', 'I', 'R', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'),
                           edge('E3', 'R', 'T', 'DISCHARGES', closes_scope='L',
                                discharge_rule='existential_elimination', discharges=[], generalizes=[])]}
        check(model)
        wrong_rule = copy.deepcopy(model)
        wrong_rule['edges'][-1].update(discharge_rule='universal_generalization', generalizes=['c'])
        with self.assertRaisesRegex(Invalid, 'WITNESS-CLOSE E3'):
            check(wrong_rule)
        wrong_generalization = copy.deepcopy(model)
        wrong_generalization['edges'][-1]['generalizes'] = ['c']
        with self.assertRaisesRegex(Invalid, 'GENERALIZATION E3'):
            check(wrong_generalization)
        fixed = copy.deepcopy(model)
        fixed['nodes'][1]['introduction_mode'] = 'fixed'
        fixed['edges'][-1].update(discharge_rule='universal_generalization', generalizes=['c'])
        with self.assertRaisesRegex(Invalid, 'GENERALIZATION E3'):
            check(fixed)

    def test_global_spelling_and_formula_reference_warning(self):
        binding = {'id': 'c', 'symbol_latex': 'c', 'domain_latex': 'X', 'depends_on': [],
                   'definition_latex': 'c=f(x)', 'well_defined': 'defined', 'domain_check': 'in X'}
        row = {'symbol_latex': 'c', 'definition_role': 'object', 'range_unit': 'X', 'interpretation': 'object'}
        model = {'symbols': [row], 'scopes': [],
                 'nodes': [node('A', 'DEFINITION'), node('C', 'CONSTRUCTION', bindings=[binding]),
                           node('R', uses_symbols=['c'], sections=[{'blocks': [{'kind': 'formula',
                                'latex': 'c', 'symbols': [copy.deepcopy(row)]}]}]), node('T', 'TARGET')],
                 'edges': [edge('E1', 'A', 'C'), edge('E2', 'C', 'R'), edge('E3', 'R', 'T')]}
        with self.assertRaisesRegex(Invalid, 'BINDING-FRESH c'):
            check(model)
        model['symbols'][0]['binding_ref'] = 'c'
        self.assertEqual(len([w for w in check(model) if w.startswith('SYMBOL-REFERENCE-RISK')]), 1)
        model['nodes'][2]['sections'][0]['blocks'][0]['symbols'][0]['binding_ref'] = 'c'
        self.assertFalse(check(model))

    def test_global_construction_is_visible_only_downstream(self):
        binding = {'id': 'a', 'symbol_latex': 'a', 'domain_latex': 'X', 'depends_on': [],
                   'definition_latex': 'a=f(x)', 'well_defined': 'defined', 'domain_check': 'in X'}
        model = {'scopes': [], 'nodes': [node('A', 'DEFINITION'),
                 node('C', 'CONSTRUCTION', bindings=[binding]),
                 node('R', uses_symbols=['a']), node('T', 'TARGET')],
                 'edges': [edge('E1', 'A', 'C'), edge('E2', 'C', 'R'), edge('E3', 'R', 'T')]}
        check(model)
        unrelated = copy.deepcopy(model)
        unrelated['nodes'][-1]['uses_symbols'] = ['a']
        unrelated['edges'] = [edge('E1', 'A', 'C'), edge('E2', 'C', 'R'), edge('E3', 'A', 'T')]
        with self.assertRaisesRegex(Invalid, 'SYMBOL-LEAK'):
            check(unrelated)

    def test_pure_hypothesis_root_and_discharge_ancestry(self):
        model = {'scopes': [{'id': 'L', 'title': 'Local', 'kind': 'local',
                             'opened_by': 'H', 'closed_by': 'E2'}],
                 'nodes': [node('H', 'HYPOTHESIS_LOCAL', 'L'), node('D', scope='L'),
                           node('T', 'TARGET')],
                 'edges': [edge('E1', 'H', 'D'),
                           edge('E2', 'D', 'T', 'DISCHARGES', closes_scope='L',
                                discharge_rule='conditional_proof', discharges=['H'], generalizes=[])]}
        check(model)
        broken = copy.deepcopy(model)
        broken['edges'][1]['discharges'] = []
        with self.assertRaisesRegex(Invalid, 'SCOPE-CLOSE|DISCHARGES'):
            check(broken)

    def test_nested_generalization_and_cross_scope_leak(self):
        model = {'scopes': [
            {'id': 'Outer', 'title': 'Outer', 'kind': 'local', 'opened_by': 'H', 'closed_by': 'E4'},
            {'id': 'Inner', 'title': 'Inner', 'kind': 'local', 'parent_scope': 'Outer',
             'opened_by': 'I', 'opening_edge': 'E2', 'closed_by': 'E3'}],
            'nodes': [node('H', 'HYPOTHESIS_LOCAL', 'Outer'),
                      node('I', 'LOCAL_INTRODUCTION', 'Outer', introduction_mode='arbitrary',
                           bindings=[{'id': 'x', 'symbol_latex': 'x', 'domain_latex': 'X', 'depends_on': []}]),
                      node('R', scope='Inner', uses_symbols=['x']), node('D', scope='Outer'),
                      node('T', 'TARGET')],
            'edges': [edge('E1', 'H', 'I'), edge('E2', 'I', 'R', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'),
                      edge('E3', 'R', 'D', 'DISCHARGES', closes_scope='Inner',
                           discharge_rule='universal_generalization', discharges=[], generalizes=['x'], uses_symbols=['x']),
                      edge('E4', 'D', 'T', 'DISCHARGES', closes_scope='Outer',
                           discharge_rule='conditional_proof', discharges=['H'], generalizes=[])]}
        check(model)
        leak = copy.deepcopy(model)
        leak['edges'].append(edge('E5', 'R', 'T'))
        with self.assertRaisesRegex(Invalid, 'SCOPE-LEAK'):
            check(leak)
        duplicate = copy.deepcopy(model)
        duplicate['nodes'][1]['bindings'].append({'id': 'x2', 'symbol_latex': 'x', 'domain_latex': 'X', 'depends_on': []})
        with self.assertRaisesRegex(Invalid, 'BINDING-FRESH'):
            check(duplicate)

    def test_witness_elimination_forbids_free_escape(self):
        model = {'scopes': [{'id': 'Witness', 'title': 'Witness', 'kind': 'local',
                             'opened_by': 'I', 'opening_edge': 'E2', 'closed_by': 'E3'}],
                 'nodes': [node('A', 'KNOWN_RESULT'),
                           node('I', 'LOCAL_INTRODUCTION', introduction_mode='witness',
                                bindings=[{'id': 'c', 'symbol_latex': 'c', 'domain_latex': 'X', 'depends_on': []}]),
                           node('R', scope='Witness', uses_symbols=['c']), node('T', 'TARGET')],
                 'edges': [edge('E1', 'A', 'I'), edge('E2', 'I', 'R', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'),
                           edge('E3', 'R', 'T', 'DISCHARGES', closes_scope='Witness',
                                discharge_rule='existential_elimination', discharges=[], generalizes=[], uses_symbols=['c'])]}
        check(model)
        escaped = copy.deepcopy(model)
        escaped['nodes'][-1]['uses_symbols'] = ['c']
        with self.assertRaisesRegex(Invalid, 'SYMBOL-LEAK'):
            check(escaped)

    def test_finite_case_pair_and_branch_isolation(self):
        model = {'scopes': [], 'nodes': [node('A', 'ASSUMPTION'),
                 node('K', 'CASE', case_mode='finite', case_input_review='Input', split_reason='Why',
                      exhaustiveness='All', case_branches=[
                          {'edge_id': 'E2', 'condition_latex': 'A', 'goal_latex': 'Q'},
                          {'edge_id': 'E3', 'condition_latex': 'B', 'goal_latex': 'Q'}]),
                 node('B1', branch_condition_latex='A'), node('B2', branch_condition_latex='B'),
                 node('C', 'COMBINE', paired_case='K', combine_reason='case_reconciliation',
                      case_closures=[{'branch_edge': 'E2', 'generalizes': [], 'discharges': ['E2'], 'rule': 'case_reconciliation'},
                                     {'branch_edge': 'E3', 'generalizes': [], 'discharges': ['E3'], 'rule': 'case_reconciliation'}]),
                 node('T', 'TARGET')],
                 'edges': [edge('E1', 'A', 'K', 'FEEDS_CASE', 'STRUCTURAL_ONLY'),
                           edge('E2', 'K', 'B1', 'CASE_BRANCH', case_condition_latex='A'), edge('E3', 'K', 'B2', 'CASE_BRANCH', case_condition_latex='B'),
                           edge('E4', 'B1', 'C', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                           edge('E5', 'B2', 'C', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                           edge('E6', 'C', 'T', 'COMBINE_PRODUCES', 'STRUCTURAL_ONLY')]}
        check(model)
        case = next(n for n in model['nodes'] if n['id'] == 'K')
        self.assertEqual(node_color_role(case), 'combine')
        self.assertEqual(estimate(case)['width'], estimate(case)['height'])
        self.assertIn('CASE', card(case, 'neutral'))
        crossed = copy.deepcopy(model)
        crossed['edges'].append(edge('E7', 'B1', 'B2'))
        with self.assertRaisesRegex(Invalid, 'CASE'):
            check(crossed)

    def test_indexed_case_uses_coverage_as_second_input(self):
        model = {'scopes': [{'id': 'General', 'title': 'General', 'kind': 'local',
                             'opened_by': 'I', 'opening_edge': 'E3', 'closed_by': 'C'}],
                 'nodes': [node('A', 'KNOWN_RESULT'),
                           node('K', 'CASE', case_mode='indexed', case_input_review='Input',
                                split_reason='Why', exhaustiveness='All indices',
                                case_branches=[{'edge_id': 'E2', 'condition_latex': 'i\\in I', 'goal_latex': 'Q(i)'}]),
                           node('I', 'LOCAL_INTRODUCTION', introduction_mode='arbitrary',
                                branch_condition_latex='i\\in I',
                                bindings=[{'id': 'i', 'symbol_latex': 'i', 'domain_latex': 'I', 'depends_on': []}]),
                           node('R', scope='General', uses_symbols=['i']),
                           node('C', 'COMBINE', paired_case='K', combine_reason='case_reconciliation',
                                case_closures=[{'branch_edge': 'E2', 'generalizes': ['i'], 'discharges': [], 'rule': 'case_reconciliation'}],
                                scope_closures=[{'scope': 'General', 'generalizes': ['i'],
                                                 'discharges': [], 'rule': 'case_reconciliation'}]),
                           node('T', 'TARGET')],
                 'edges': [edge('E1', 'A', 'K', 'FEEDS_CASE', 'STRUCTURAL_ONLY'),
                           edge('E2', 'K', 'I', 'CASE_BRANCH', case_condition_latex='i\\in I'),
                           edge('E3', 'I', 'R', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'),
                           edge('E4', 'R', 'C', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                           edge('E5', 'A', 'C', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                           edge('E6', 'C', 'T', 'COMBINE_PRODUCES', 'STRUCTURAL_ONLY')]}
        check(model)
        missing = copy.deepcopy(model)
        missing['edges'] = [e for e in missing['edges'] if e['id'] != 'E5']
        with self.assertRaisesRegex(Invalid, 'CASE'):
            check(missing)

    def test_dependency_and_induction_roles(self):
        model = {'scopes': [{'id': 'Step', 'title': 'Step', 'kind': 'induction',
                             'opened_by': 'I', 'opening_edge': 'E2', 'closed_by': 'E4'}],
                 'nodes': [node('A', 'DEFINITION'), node('B', 'LEMMA'), node('P', 'KNOWN_RESULT'),
                           node('I', 'LOCAL_INTRODUCTION', introduction_mode='arbitrary',
                                bindings=[{'id': 'n', 'symbol_latex': 'n', 'domain_latex': 'N', 'depends_on': []}]),
                           node('H', 'HYPOTHESIS_LOCAL', 'Step', uses_symbols=['n']),
                           node('R', scope='Step', uses_symbols=['n']), node('S', 'LEMMA'),
                           node('C', 'COMBINE', combine_reason='induction',
                                induction_obligations={'base': ['B'], 'step': ['S'], 'principle': 'P'}),
                           node('T', 'TARGET')],
                 'edges': [edge('E1', 'A', 'I'), edge('E2', 'I', 'H', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'),
                           edge('E3', 'H', 'R'), edge('E4', 'R', 'S', 'DISCHARGES', closes_scope='Step',
                                discharge_rule='induction_generalization', discharges=['H'],
                                generalizes=['n'], uses_symbols=['n']),
                           edge('E5', 'B', 'C', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                           edge('E6', 'S', 'C', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                           edge('E7', 'P', 'C', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                           edge('E8', 'C', 'T', 'COMBINE_PRODUCES', 'STRUCTURAL_ONLY')]}
        check(model)
        missing = copy.deepcopy(model)
        missing['nodes'][-2]['induction_obligations'].pop('base')
        with self.assertRaisesRegex(Invalid, 'INDUCTION'):
            check(missing)
        dependent = copy.deepcopy(model)
        dependent['nodes'][3]['bindings'][0]['depends_on'] = ['future']
        with self.assertRaisesRegex(Invalid, 'BINDING-DEPENDENCY'):
            check(dependent)

        strong = copy.deepcopy(model)
        strong['edges'] = [e for e in strong['edges'] if e['id'] != 'E5']
        induction = next(n for n in strong['nodes'] if n['id'] == 'C')
        induction['induction_obligations'] = {'base': [], 'step': ['S'], 'principle': 'P',
                                              'vacuous_base': 'The least index has an empty earlier-index hypothesis.'}
        check(strong)

        structural = copy.deepcopy(model)
        structural['nodes'].extend([node('D1', scope='Step', uses_symbols=['n']),
                                    node('D2', scope='Step', uses_symbols=['n']),
                                    node('CS', 'COMBINE', 'Step', uses_symbols=['n'],
                                         combine_reason='independent_results')])
        structural['edges'] = [e for e in structural['edges'] if e['id'] != 'E3']
        structural['edges'].extend([
            edge('E9', 'H', 'D1', uses_symbols=['n']), edge('E10', 'H', 'D2', uses_symbols=['n']),
            edge('E11', 'D1', 'CS', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
            edge('E12', 'D2', 'CS', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
            edge('E13', 'CS', 'R', 'COMBINE_PRODUCES', 'STRUCTURAL_ONLY')])
        check(structural)

        multiple_steps = copy.deepcopy(model)
        multiple_steps['scopes'].append({'id': 'Step2', 'title': 'Step2', 'kind': 'induction',
                                          'opened_by': 'I2', 'opening_edge': 'E10', 'closed_by': 'E12'})
        multiple_steps['nodes'].extend([
            node('I2', 'LOCAL_INTRODUCTION', introduction_mode='arbitrary',
                 bindings=[{'id': 'k', 'symbol_latex': 'n', 'domain_latex': 'N', 'depends_on': []}]),
            node('H2', 'HYPOTHESIS_LOCAL', 'Step2', uses_symbols=['k']),
            node('R2', scope='Step2', uses_symbols=['k']), node('S2', 'LEMMA')])
        multiple_steps['edges'].extend([
            edge('E9', 'A', 'I2'), edge('E10', 'I2', 'H2', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'),
            edge('E11', 'H2', 'R2'),
            edge('E12', 'R2', 'S2', 'DISCHARGES', closes_scope='Step2',
                 discharge_rule='induction_generalization', discharges=['H2'],
                 generalizes=['k'], uses_symbols=['k']),
            edge('E13', 'S2', 'C', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY')])
        induction2 = next(n for n in multiple_steps['nodes'] if n['id'] == 'C')
        induction2['induction_obligations']['step'] = ['S', 'S2']
        check(multiple_steps)
        omitted = copy.deepcopy(multiple_steps)
        next(n for n in omitted['nodes'] if n['id'] == 'C')['induction_obligations']['step'] = ['S']
        with self.assertRaisesRegex(Invalid, 'INDUCTION'):
            check(omitted)

    def test_forall_epsilon_exists_delta_dependency_order(self):
        model = {'scopes': [{'id': 'Epsilon', 'title': 'Epsilon', 'kind': 'local',
                             'opened_by': 'I', 'opening_edge': 'E2', 'closed_by': 'E4'}],
                 'nodes': [node('A', 'DEFINITION'),
                           node('I', 'LOCAL_INTRODUCTION', introduction_mode='arbitrary',
                                bindings=[{'id': 'eps', 'symbol_latex': r'\varepsilon',
                                           'domain_latex': r'(0,\infty)', 'depends_on': []}]),
                           node('C', 'CONSTRUCTION', 'Epsilon', uses_symbols=['eps', 'delta'],
                                bindings=[{'id': 'delta', 'symbol_latex': r'\delta',
                                           'domain_latex': r'(0,\infty)', 'definition_latex': r'\delta=\varepsilon/2',
                                           'depends_on': ['eps'], 'well_defined': 'Positive half',
                                           'domain_check': 'Positive'}]),
                           node('R', scope='Epsilon', uses_symbols=['eps']), node('T', 'TARGET')],
                 'edges': [edge('E1', 'A', 'I'), edge('E2', 'I', 'C', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'),
                           edge('E3', 'C', 'R', introduces_exists=['delta'], uses_symbols=['eps', 'delta']),
                           edge('E4', 'R', 'T', 'DISCHARGES', closes_scope='Epsilon',
                                discharge_rule='universal_generalization', discharges=[],
                                generalizes=['eps'], uses_symbols=['eps'])]}
        check(model)
        self.assertEqual(quantifier_dependencies(model), [('eps', 'delta')])
        reversed_scope = copy.deepcopy(model)
        construction = next(n for n in reversed_scope['nodes'] if n['id'] == 'C')
        construction['scope'] = None
        with self.assertRaisesRegex(Invalid, 'SCOPE|BINDING-DEPENDENCY'):
            check(reversed_scope)

    def test_nested_induction_closes_inner_step_before_outer_step(self):
        model = {'scopes': [
            {'id': 'Outer', 'title': 'Outer', 'kind': 'induction',
             'opened_by': 'I0', 'opening_edge': 'E2', 'closed_by': 'E11'},
            {'id': 'Inner', 'title': 'Inner', 'kind': 'induction', 'parent_scope': 'Outer',
             'opened_by': 'I1', 'opening_edge': 'E4', 'closed_by': 'E6'}],
            'nodes': [node('A', 'DEFINITION'), node('BI', 'LEMMA'), node('PI', 'KNOWN_RESULT'),
                      node('BO', 'LEMMA'), node('PO', 'KNOWN_RESULT'),
                      node('I0', 'LOCAL_INTRODUCTION', introduction_mode='arbitrary',
                           bindings=[{'id': 'n', 'symbol_latex': 'n', 'domain_latex': 'N', 'depends_on': []}]),
                      node('H0', 'HYPOTHESIS_LOCAL', 'Outer', uses_symbols=['n']),
                      node('I1', 'LOCAL_INTRODUCTION', 'Outer', introduction_mode='arbitrary', uses_symbols=['n', 'k'],
                           bindings=[{'id': 'k', 'symbol_latex': 'k', 'domain_latex': 'K', 'depends_on': ['n']}]),
                      node('H1', 'HYPOTHESIS_LOCAL', 'Inner', uses_symbols=['n', 'k']),
                      node('R1', scope='Inner', uses_symbols=['n', 'k']),
                      node('S1', 'LEMMA', 'Outer', uses_symbols=['n']),
                      node('CI', 'COMBINE', 'Outer', combine_reason='induction', uses_symbols=['n'],
                           induction_obligations={'base': ['BI'], 'step': ['S1'], 'principle': 'PI'}),
                      node('T1', 'LEMMA', 'Outer', uses_symbols=['n']),
                      node('S0', 'LEMMA'),
                      node('CO', 'COMBINE', combine_reason='induction',
                           induction_obligations={'base': ['BO'], 'step': ['S0'], 'principle': 'PO'}),
                      node('T', 'TARGET')],
            'edges': [edge('E1', 'A', 'I0'), edge('E2', 'I0', 'H0', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'),
                      edge('E3', 'H0', 'I1', uses_symbols=['n']),
                      edge('E4', 'I1', 'H1', 'OPENS_SCOPE', 'STRUCTURAL_ONLY'),
                      edge('E5', 'H1', 'R1', uses_symbols=['n', 'k']),
                      edge('E6', 'R1', 'S1', 'DISCHARGES', closes_scope='Inner',
                           discharge_rule='induction_generalization', discharges=['H1'],
                           generalizes=['k'], uses_symbols=['n', 'k']),
                      edge('E7', 'BI', 'CI', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                      edge('E8', 'PI', 'CI', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                      edge('E9', 'S1', 'CI', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                      edge('E10', 'CI', 'T1', 'COMBINE_PRODUCES', 'STRUCTURAL_ONLY'),
                      edge('E11', 'T1', 'S0', 'DISCHARGES', closes_scope='Outer',
                           discharge_rule='induction_generalization', discharges=['H0'],
                           generalizes=['n'], uses_symbols=['n']),
                      edge('E12', 'BO', 'CO', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                      edge('E13', 'PO', 'CO', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                      edge('E14', 'S0', 'CO', 'FEEDS_COMBINE', 'STRUCTURAL_ONLY'),
                      edge('E15', 'CO', 'T', 'COMBINE_PRODUCES', 'STRUCTURAL_ONLY')]}
        check(model)


if __name__ == '__main__':
    unittest.main()
