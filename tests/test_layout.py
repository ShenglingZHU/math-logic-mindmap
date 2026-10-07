"""Topology fixtures exercise placement independently of proof prose validation."""
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/math-logic-mindmap/scripts'))
from math_logic_mindmap.layout import geometry, metrics, combine_feed_details
from math_logic_mindmap.model import validate
from math_logic_mindmap.common import read_json
from math_logic_mindmap.render import layout

def fixture(edges, scopes=None, intuition=False):
    ids=sorted(set(i for e in edges for i in e))
    nodes={i:{'id':i,'type':'COMBINE' if i.startswith('C') else 'TARGET' if i=='T' else 'DERIVATION','title':i,'short_role':'说明'} for i in ids}
    incoming={i:[] for i in ids}; outgoing={i:[] for i in ids}
    for a,b in edges:
        outgoing[a].append(b); incoming[b].append(a)
    order=[]; ranks={}
    while len(order)<len(ids):
        for i in ids:
            if i not in order and all(p in order for p in incoming[i]):
                order.append(i); ranks[i]=max([ranks[p]+1 for p in incoming[i]] or [0])
    for scope,members in (scopes or {}).items():
        for i in members:
            nodes[i]['scope']=scope
    if intuition:
        nodes['I']={'id':'I','type':'INTUITION','title':'直觉','short_role':'非证明'}
        incoming['I']=[]; outgoing['I']=[]; ranks['I']=0; order.append('I')
    model={'nodes':list(nodes.values()),'edges':[{'id':f'E{k}','source':a,'target':b} for k,(a,b) in enumerate(edges)],'target_id':'T','scopes':[{'id':s} for s in scopes or {}]}
    return model,{'nodes':nodes,'incoming':incoming,'outgoing':outgoing,'order':order,'ranks':ranks}

class LayoutTests(unittest.TestCase):
    def test_generated_canvas_uses_downward_orthogonal_routes(self):
        model=read_json(ROOT/'tests/fixtures/canonical-smoke.proof.json')
        canvas=layout(model,validate(model))
        self.assertEqual(canvas['metadata']['proofRouting']['profile'],'downward-orthogonal')
        self.assertFalse(any('proofGeometry' in edge for edge in canvas['edges']))
        from math_logic_mindmap.routing import require_clear
        report=require_clear(canvas)
        self.assertEqual(report['status'],'PASS')
        self.assertTrue(all(len(points) in (2,4) for points in report['paths'].values()))

    def test_topologies(self):
        cases=[
            ([('A','B'),('B','T')],None,False),
            ([('A','B'),('A','D'),('B','C'),('D','C'),('C','T')],None,False),
            ([('A','C'),('B','C'),('D','C'),('F','C'),('C','T')],None,False),
            ([('A','B'),('B','C'),('D','C'),('C','T')],{'One':['A','B'],'Two':['D']},False),
            ([('A','T')],None,True),
        ]
        for edges,scopes,intuition in cases:
            m,a=fixture(edges,scopes,intuition)
            boxes,layers,spine=geometry(m,a)
            self.assertEqual(geometry(m,a),(boxes,layers,spine))
            for source,target in edges:
                self.assertGreaterEqual(boxes[target]['y']-boxes[source]['y']-boxes[source]['height'],56)
            for i,n in boxes.items():
                for j,o in boxes.items():
                    if i<j:
                        self.assertFalse(n['x']<o['x']+o['width']+24 and o['x']<n['x']+n['width']+24 and n['y']<o['y']+o['height']+24 and o['y']<n['y']+n['height']+24)
            for n in m['nodes']:
                if n['type']=='COMBINE':
                    t=a['outgoing'][n['id']][0]
                    self.assertEqual(boxes[n['id']]['x']+90,boxes[t]['x']+boxes[t]['width']/2)

    def test_feature_layout_acceptance(self):
        m=read_json(ROOT/'tests/fixtures/feature-coverage.proof.json'); a=validate(m)
        canvas=layout(m,a); new=metrics(m,canvas)
        self.assertEqual(new['combine_result_offset'],0)
        from math_logic_mindmap.routing import analyze
        routing=analyze(canvas)
        self.assertEqual(routing['status'],'PASS')
        details=combine_feed_details(m,canvas,routing)
        self.assertEqual(len(details),6)
        self.assertEqual({item['target'] for item in details},{'C1','C2'})
        self.assertTrue(all(e['fromSide']=='bottom' and e['toSide']=='top' for e in canvas['edges']))

    def test_automatic_layout_is_clear_and_clustered(self):
        m=read_json(ROOT/'tests/fixtures/feature-coverage.proof.json');a=validate(m)
        canvas=layout(m,a);report=metrics(m,canvas)
        details=combine_feed_details(m,canvas)
        from math_logic_mindmap.routing import analyze
        routing=analyze(canvas)
        self.assertEqual(routing['status'],'PASS')
        self.assertFalse(routing['conflicts'])
        # Baseline: gap=956, total dx=3440, max dx=824, balance=48,
        # long edges=1, combine long reuse=0. Ceilings retain the agreed
        # 15%/128px and 20%/160px quality margins without freezing coordinates.
        self.assertLessEqual(report['max_vertical_gap'],1104)
        self.assertLessEqual(report['combine_feed_horizontal_total'],4128)
        self.assertLessEqual(report['combine_feed_horizontal_max'],992)
        self.assertLessEqual(report['combine_cluster_balance_offset'],128)
        self.assertLessEqual(report['long_edges'],1)
        self.assertEqual(report['combine_long_reuse_count'],0)
        self.assertEqual(len(details),6)
        self.assertTrue(all(len(routing['paths'][item['edge']]) in (2,4) for item in details))
        boxes={n['id']:n for n in canvas['nodes']}
        target=boxes[m['target_id']];header=boxes['UIHeader']
        self.assertEqual(header['x']+header['width']/2,target['x']+target['width']/2)
        widths={boxes[node['id']]['width'] for node in m['nodes']}
        self.assertTrue({720,800}.issubset(widths))
        proof_boxes={node['id']:boxes[node['id']] for node in m['nodes']}
        for first_id,first in proof_boxes.items():
            for second_id,second in proof_boxes.items():
                if first_id >= second_id:
                    continue
                self.assertFalse(first['x'] < second['x']+second['width']+24
                                 and second['x'] < first['x']+first['width']+24
                                 and first['y'] < second['y']+second['height']+24
                                 and second['y'] < first['y']+first['height']+24)
        group=boxes['GL1']
        contained={nid for nid,box in proof_boxes.items()
                   if box['x'] >= group['x'] and box['y'] >= group['y']
                   and box['x']+box['width'] <= group['x']+group['width']
                   and box['y']+box['height'] <= group['y']+group['height']}
        expected={node['id'] for node in m['nodes'] if node.get('scope')=='L1'}
        self.assertEqual(contained,expected)
