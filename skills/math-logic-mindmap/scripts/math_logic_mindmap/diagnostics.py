"""Reproducible diagnostics; counts are conflicts, not independent causes."""
from collections import Counter, defaultdict
from .routing import analyze


def port_loads(canvas):
    occupied = defaultdict(list)
    for edge in canvas['edges']:
        for end in ('from', 'to'):
            occupied[(edge[end + 'Node'], edge[end + 'Side'])].append(edge['id'])
    return [{'node': n, 'side': s, 'edge_count': len(es)}
            for (n, s), es in sorted(occupied.items())]


def port_collisions(canvas):
    occupied = defaultdict(list)
    for edge in canvas['edges']:
        route = edge.get('proofRoute', {})
        for end in ('from', 'to'):
            occupied[(edge[end + 'Node'], edge[end + 'Side'], route.get(end + 'Offset', 0))].append(edge['id'])
    return [{'node': n, 'side': s, 'offset': offset, 'edges': sorted(es)}
            for (n, s, offset), es in sorted(occupied.items()) if len(es) > 1]


def summarize(canvas, routing=None):
    routing = routing or analyze(canvas)
    edges = {e['id']: e for e in canvas['edges']}
    affected, kinds, sources = set(), Counter(), Counter()
    for conflict in routing['conflicts']:
        ids = [conflict['edge']]
        if 'other_edge' in conflict:
            ids.append(conflict['other_edge'])
            kinds[conflict['code']] += 1
        else:
            kinds[conflict['code']] += 1
        affected.update(ids)
        sources.update({edges[eid]['fromNode'] for eid in ids})
    def bounds(cards):
        return ([min(n['x'] for n in cards), min(n['y'] for n in cards),
                 max(n['x'] + n['width'] for n in cards), max(n['y'] + n['height'] for n in cards)] if cards else None)
    cards = [n for n in canvas['nodes'] if n['type'] != 'group']
    incoming, outgoing = Counter(e['toNode'] for e in edges.values()), Counter(e['fromNode'] for e in edges.values())
    return {'status': routing['status'], 'conflict_count': len(routing['conflicts']),
            'classification': dict(kinds), 'affected_edges': sorted(affected),
            'affected_edge_count': len(affected), 'source_conflict_counts': dict(sources),
            'port_loads': port_loads(canvas), 'port_collisions': port_collisions(canvas),
            'unknown_edges': routing['unknown_edges'],
            'crossing_count': len(routing['crossings']), 'edge_count': len(edges),
            'model_node_count': sum(not n['id'].startswith('UI') for n in cards),
            'max_indegree': max(incoming.values(), default=0), 'max_outdegree': max(outgoing.values(), default=0),
            'card_bounds': bounds(cards), 'proof_bounds': bounds([n for n in cards if not n['id'].startswith('UI')]),
            'route_summary': {'total_length': sum(sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(p,p[1:])) for p in routing['paths'].values()),
                              'max_bends': max((max(0, len(p)-2) for p in routing['paths'].values()), default=0)},
            'visual': 'UNREVIEWED', 'note': 'Crossings are diagnostic and do not count as conflicts.'}
