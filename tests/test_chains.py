"""Continuous expression/application rendering and fail-closed dependencies."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/math-logic-mindmap/scripts'))
from math_logic_mindmap.common import Invalid, read_json, write_json
from math_logic_mindmap.chains import compile_chain, require_chains, validate_chain
from math_logic_mindmap.model import validate
from math_logic_mindmap.render import generate_notes, transform_body
from math_logic_mindmap.bundle import build


def equality_fixture():
    syms=[{'symbol_latex':s,'definition_role':d,'range_unit':'实数','interpretation':meaning} for s,d,meaning in [('S','待计算表达式','代入已知数值后求值'),('x','给定变量','本例取三')]]
    def b(id,latex,symbols):return {'id':id,'kind':'formula','latex':latex,'symbols':symbols}
    first=b('start','S=2(x+1)',syms)
    basis=b('given','x=3',syms[1:])
    n={'id':'C','type':'COMBINE','combine_inputs':['A','B'],'start_input':'A','combine_output_latex':'S=8',
       'input_usage':[{'node':'A','formula_ref':'core','step_id':'start','mode':'start'},{'node':'B','formula_ref':'core','step_id':'given','mode':'basis'}],
       'derivation':[first,basis,b('substitute','S=2(3+1)',syms[:1]),b('result','S=8',syms[:1])],
       'derivation_chain':{'rows':[{'kind':'expression','step_id':'start','split_at':1},{'kind':'apply','step_id':'given','source':{'node':'B','formula_ref':'core'},'name':'给定数值','next_step':'substitute'},{'kind':'expression','step_id':'substitute','split_at':1,'continuation':True},{'kind':'expression','step_id':'result','split_at':1,'continuation':True}],'symbols':syms}}
    nodes={key:{'id':key,'formula_latex':f['latex'],'sections':[{'heading':'内容','blocks':[f]}]} for key,f in [('A',first),('B',basis)]}
    return n,nodes

def auxiliary_transform_fixture():
    syms=[{'symbol_latex':s,'definition_role':d,'range_unit':'实数','interpretation':meaning}
          for s,d,meaning in [('S','待化简表达式','代入辅助结果后求值'),('u','辅助变量','本例由一加二得到三')]]
    def b(id,latex,symbols):return {'id':id,'kind':'formula','latex':latex,'symbols':symbols}
    start=b('start','S=2(u+1)',syms)
    aux_step=b('aux_step','u=1+2',syms[1:])
    aux_result=b('aux_result','u=3',syms[1:])
    result=b('result','S=8',syms[:1])
    source={'id':'A','title':'待化简式','navigation':{'role':'提供主链起点。'},
            'formula_latex':start['latex'],'sections':[{'heading':'内容','blocks':[start]}]}
    node={'id':'X','type':'TRANSFORM','title':'代入','transform_input':'A','transform_output_latex':'S=8',
          'input_review':[{'node':'A','formula_ref':'core','contribution':'提供待化简表达式。'}],
          'input_usage':[{'node':'A','formula_ref':'core','step_id':'start','mode':'start'}],
          'start_input':'A','transform_motivation':'求出辅助量后代入。','transform_method':'先完成辅助计算，再代入主链。',
          'output_handoff':{'explanation':'得到数值。','downstream_use':'供后续使用。'},
          'derivation':[start,aux_step,aux_result,result],
          'derivation_chain':{'rows':[{'kind':'expression','step_id':'start','split_at':1},
              {'kind':'apply','step_id':'aux_result','auxiliary_ref':'u_value','name':'辅助计算','next_step':'result'},
              {'kind':'expression','step_id':'result','split_at':1,'continuation':True}],
              'symbols':syms,'auxiliaries':[{'id':'u_value','steps':['aux_step','aux_result'],'result_ref':'aux_result'}]}}
    return node,{'A':source,'X':node}


class ChainTests(unittest.TestCase):
    def setUp(self):
        self.model=read_json(ROOT/'tests/fixtures/canonical-smoke.proof.json')
        self.nodes={n['id']:n for n in self.model['nodes']}

    def test_equality_continuation_and_long_arrow(self):
        n,nodes=equality_fixture();validate_chain(n,nodes)
        latex=compile_chain(n)['latex']
        self.assertIn('S&=2(x+1)',latex)
        self.assertIn('&=2(3+1)',latex)
        self.assertIn('&=8',latex)
        self.assertIn(r'\vphantom{\boxed{',latex)
        self.assertIn(r'\rule{0pt}{3em}\right\downarrow',latex)
        self.assertEqual(latex.count(r'\right\downarrow'),1)
        self.assertIn(r'(\text{给定数值，B})',latex)
        self.assertIn(r'(\text{给定数值, B})',compile_chain(n,'en')['latex'])

    def test_basis_titles_use_source_ids_only(self):
        from math_logic_mindmap.chains import tex_text
        kinds=set()
        aux_node,aux_nodes=auxiliary_transform_fixture()
        cases=[(self.nodes['C1'],self.nodes),(self.nodes['X1'],self.nodes),(aux_node,aux_nodes)]
        for node,_ in cases:
            latex=compile_chain(node)['latex']
            for row in node['derivation_chain']['rows']:
                if row['kind']!='apply':continue
                kind=next(k for k in ('source','external','auxiliary_ref') if k in row)
                kinds.add(kind)
                title=row['name']+('，'+row['source']['node'] if kind=='source' else '')
                self.assertIn(r'(\text{'+tex_text(title)+'})',latex)
                if kind!='source':
                    self.assertNotIn(r'(\text{'+tex_text(row['name'])+'，',latex)
        self.assertEqual(kinds,{'source','external','auxiliary_ref'})

    def test_one_display_one_table_after_entire_main_chain(self):
        notes=generate_notes(self.model)
        for nid in ('C1','X1'):
            text=notes[f'note/{self.model["slug"]}/{nid}.md']
            end_heading='## 合并结果\n' if nid=='C1' else '## 变换结果\n'
            section=text.split('### 连续主链\n')[1].split(end_heading)[0]
            self.assertEqual(section.count('$$'),2)
            self.assertEqual(section.count('| 符号 |'),1)
            end=section.rfind('$$')
            self.assertGreater(section.index('| 符号 |'),end)
            self.assertNotIn('[[',section[:end])
            output=self.nodes[nid].get('combine_output_latex',self.nodes[nid].get('transform_output_latex'))
            self.assertIn(output,section.replace('&',''))

    def test_inequality_and_logic_do_not_turn_into_equalities(self):
        for nid,relation in [('C1',r'\le'),('X1',r'\le')]:
            latex=compile_chain(self.nodes[nid])['latex']
            self.assertIn(relation,latex)
            self.assertEqual(latex.count(r'\right\downarrow'),sum(r['kind']=='apply' for r in self.nodes[nid]['derivation_chain']['rows']))

    def test_broken_chain_connections_and_references(self):
        for case in ('next','source','missing_use','duplicate','symbol','last','alignment','continuation','hidden'):
            model=copy.deepcopy(self.model)
            n=next(n for n in model['nodes'] if n['id']=='C1');rows=n['derivation_chain']['rows']
            app=next(r for r in rows if r['kind']=='apply')
            if case=='next':app['next_step']='input1'
            elif case=='source':app['source']['node']='A1'
            elif case=='missing_use':rows.remove(app)
            elif case=='duplicate':rows.insert(1,copy.deepcopy(rows[0]))
            elif case=='symbol':n['derivation_chain']['symbols'].pop()
            elif case=='last':rows.pop()
            elif case=='alignment':rows[0]['split_at']=2
            elif case=='continuation':rows[0]['continuation']=True
            else:n['derivation'].insert(-1,{'kind':'prose','id':'hidden','text':'不应被静默遗漏。'})
            with self.subTest(case=case),self.assertRaises(Invalid):validate(model)

    def test_missing_chain_blocks_build(self):
        next(n for n in self.model['nodes'] if n['id']=='C1').pop('derivation_chain')
        validate(self.model)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);p=root/'proof'/self.model['slug']/f'{self.model["slug"]}.proof.json';write_json(p,self.model)
            with self.assertRaisesRegex(Invalid,'CHAIN'):build(root,p)

    def test_multiline_basis_keeps_left_aligned_name_and_arrow(self):
        node=copy.deepcopy(self.nodes['C1'])
        basis=next(b for b in node['derivation'] if b['id']=='input2')
        basis['latex']=r'\begin{aligned}c&>0\\d&>0\end{aligned}'
        text=compile_chain(node)['latex']
        self.assertIn(r'\boxed{\begin{aligned}&',text)
        self.assertIn(r'\\[0.4em]&(\text{',text)
        self.assertIn(r'\right\downarrow\qquad',text)

    def test_structured_multiline_start_and_basis_remain_inside_chain(self):
        node, nodes = equality_fixture()
        start = r'\left\{\begin{aligned}S&=2(x+1)\\x&>0\end{aligned}\right.'
        basis = r'\begin{aligned}x&=3\\x&>0\end{aligned}'
        node['derivation'][0]['latex'] = nodes['A']['formula_latex'] = start
        nodes['A']['sections'][0]['blocks'][0]['latex'] = start
        node['derivation'][1]['latex'] = nodes['B']['formula_latex'] = basis
        nodes['B']['sections'][0]['blocks'][0]['latex'] = basis
        node['derivation_chain']['rows'][0]['split_at'] = 0
        for row in node['derivation_chain']['rows'][1:]:
            row.pop('continuation', None)
        validate_chain(node, nodes)
        rendered = compile_chain(node)['latex']
        self.assertIn('&' + start, rendered)
        self.assertIn(basis, rendered)
        self.assertEqual(rendered.count(r'\right\downarrow'), 1)

    def test_auxiliary_is_complete_inside_one_basis_box(self):
        node,nodes=auxiliary_transform_fixture();validate_chain(node,nodes)
        latex=compile_chain(node)['latex']
        aux=node['derivation_chain']['auxiliaries'][0]
        pool={b['id']:b for b in node['derivation']}
        for step in aux['steps']:
            self.assertIn(pool[step]['latex'],latex)
        note=transform_body({'slug':'aux','nodes':list(nodes.values())},node)
        section=note.split('### 连续主链\n')[1].split('## 变换结果\n')[0]
        self.assertNotIn('### 辅助计算',section)
        self.assertEqual(section.count('$$'),2)
        self.assertEqual(section.count('| 符号 |'),1)

    def test_transform_uses_the_same_inline_auxiliary_rendering(self):
        node,nodes=auxiliary_transform_fixture();validate_chain(node,nodes)
        body=transform_body({'slug':'aux','nodes':list(nodes.values())},node)
        section=body.split('### 连续主链\n')[1].split('## 变换结果\n')[0]
        self.assertIn('u=1+2',section)
        self.assertIn('u=3',section)
        self.assertNotIn('### 辅助计算',body)
        self.assertEqual(section.count('$$'),2)
        self.assertEqual(section.count('| 符号 |'),1)

    def test_auxiliary_requires_formula_steps_and_one_apply(self):
        for case in ('prose','duplicate_use','wrong_result','symbol'):
            node,nodes=auxiliary_transform_fixture()
            node=copy.deepcopy(node);nodes={**nodes,'X':node}
            aux=node['derivation_chain']['auxiliaries'][0]
            if case=='prose':
                node['derivation'].insert(1,{'kind':'prose','id':'aux_prose','text':'不应作为辅助公式步骤。'})
                aux['steps'].insert(0,'aux_prose')
            elif case=='duplicate_use':
                row=next(r for r in node['derivation_chain']['rows'] if 'auxiliary_ref' in r)
                node['derivation_chain']['rows'].insert(-1,copy.deepcopy(row))
            else:
                if case=='wrong_result':
                    aux['result_ref']='aux_step'
                else:
                    extra=copy.deepcopy(next(b for b in node['derivation'] if b['id']=='aux_step')['symbols'][0])
                    extra['symbol_latex']='new_aux_symbol'
                    next(b for b in node['derivation'] if b['id']=='aux_step')['symbols'].append(extra)
            with self.subTest(case=case),self.assertRaises(Invalid):validate_chain(node,nodes)


if __name__=='__main__':unittest.main()
