"""Deterministic display-layer placement; no claim about host-rendered routes."""
from collections import defaultdict, Counter
from html import escape
from .model import estimate
from .routing import AUTO_LAYER_GAP, NODE_GAP, PARALLEL_CLEARANCE, TURN_STUB
from .scope_semantics import scope_members

VERSION = 'clearance-adaptive-1'

def geometry(model, analysis, config=None):
    nodes = analysis['nodes']
    incoming, outgoing = analysis['incoming'], analysis['outgoing']
    layers = dict(analysis['ranks'])
    for i in reversed(analysis['order']):
        if outgoing[i]:
            layers[i] = min(layers[j] for j in outgoing[i]) - 1
    bottom = max(layers.values())
    # Disconnected intuition remains a separate reading region.
    for i in nodes:
        if nodes[i]['type'] == 'INTUITION':
            layers[i] = analysis['ranks'][i]
    spine = [model['target_id']]
    while incoming[spine[-1]]:
        spine.append(min(incoming[spine[-1]], key=lambda i: (-analysis['ranks'][i], i)))
    spine.reverse()
    parent = {i: i for i in nodes}
    def find(i):
        while parent[i] != i:
            i = parent[i]
        return i
    def join(a,b):
        parent[find(a)] = find(b)
    # The spine is a reading order, not a rigid geometric column. Keeping every
    # spine node in one unit makes a reused fact draw through all intervening
    # cards. Only operation/result pairs remain rigidly aligned.
    for i,n in nodes.items():
        if n['type'] in ('COMBINE', 'TRANSFORM'):
            join(i, outgoing[i][0])
    units = defaultdict(list)
    for i in sorted(nodes):
        units[find(i)].append(i)
    sizes = {i: estimate(n, config) for i,n in nodes.items()}
    column_step = max(448, max(size['width'] for size in sizes.values()) + NODE_GAP)
    ys, y = {}, 0
    ordered_layers = sorted(set(layers.values()))
    for layer_index, layer in enumerate(ordered_layers):
        ys[layer] = y
        lane_count = 1
        if layer_index + 1 < len(ordered_layers):
            following = ordered_layers[layer_index + 1]
            crossing = [e for e in model['edges']
                        if layers[e['source']] <= layer and layers[e['target']] >= following]
            target_load = Counter(e['target'] for e in crossing)
            source_load = Counter(e['source'] for e in crossing)
            lane_count = max([1, *target_load.values(), *source_load.values()])
        gap = max(AUTO_LAYER_GAP, 2 * TURN_STUB + (lane_count - 1) * PARALLEL_CLEARANCE)
        y += max(sizes[i]['height'] for i in nodes if layers[i] == layer) + gap
    centers = {}
    def valid(unit, x, current):
        for i in units[unit]:
            for other, cx in current.items():
                if other == unit:
                    continue
                for j in units[other]:
                    if layers[i] == layers[j] and abs(x-cx) < (sizes[i]['width']+sizes[j]['width'])/2+NODE_GAP:
                        return False
        return True
    main = find(model['target_id'])
    centers[main] = 0
    ordered = sorted(units, key=lambda u: (-max(layers[i] for i in units[u]), u))
    for u in ordered:
        if u in centers:
            continue
        targets = [centers[find(j)] for i in units[u] for j in outgoing[i] if find(j) in centers]
        preferred = sum(targets)/len(targets) if targets else 0
        candidates = [round(preferred)+sign*column_step*k for k in range(len(units)+1) for sign in (-1,1)]
        centers[u] = next(x for x in candidates if valid(u,x,centers))
    def score(current):
        positions = {i: current[find(i)] for i in nodes}
        crossings = 0
        edges = model['edges']
        for k,e in enumerate(edges):
            for f in edges[k+1:]:
                a,b,c,d=e['source'],e['target'],f['source'],f['target']
                if len({a,b,c,d}) == 4 and layers[a] == layers[c] and layers[b] == layers[d]:
                    crossings += (positions[a]-positions[c])*(positions[b]-positions[d]) < 0
        distance = sum(abs(positions[e['source']]-positions[e['target']]) for e in edges)
        return crossings, distance, max(current.values())-min(current.values())
    for sweep in range(8):
        changed = False
        for u in (ordered if sweep%2 else list(reversed(ordered))):
            if u == main:
                continue
            neighbors = [centers[find(j)] for i in units[u] for j in incoming[i]+outgoing[i] if find(j)!=u]
            if not neighbors:
                continue
            mean = round(sum(neighbors)/len(neighbors))
            old = score(centers)
            for x in sorted({mean, mean-column_step, mean+column_step, centers[u]}, key=lambda x:(abs(x-mean),x)):
                trial = {**centers,u:x}
                if valid(u,x,centers) and score(trial)<old:
                    centers, old, changed = trial, score(trial), True
        if not changed:
            break
    scopes = {s['id']: list(scope_members(model, s['id'])) for s in model.get('scopes',[])}
    intuition = [i for i,n in nodes.items() if n['type']=='INTUITION' or not n.get('strict',True)]
    if intuition:
        scopes['__intuition'] = intuition
    # Keep unrelated cards outside each local scope's bounding box.
    for _ in range(len(units)*2):
        changed = False
        for members in scopes.values():
            if not members:
                continue
            left=min(centers[find(i)]-sizes[i]['width']/2 for i in members)-24
            right=max(centers[find(i)]+sizes[i]['width']/2 for i in members)+24
            top=min(ys[layers[i]] for i in members)-48
            end=max(ys[layers[i]]+sizes[i]['height'] for i in members)+24
            for u in ordered:
                outsiders=[i for i in units[u] if i not in members and ys[layers[i]]<end and ys[layers[i]]+sizes[i]['height']>top]
                if not outsiders or not any(centers[u]+sizes[i]['width']/2>left and centers[u]-sizes[i]['width']/2<right for i in outsiders):
                    continue
                if any(i in members for i in units[u]):
                    continue  # validator reports incompatible interleaved scopes
                half=max(sizes[i]['width']/2 for i in units[u])
                choices=sorted([left-half-48,right+half+48],key=lambda x:(abs(x-centers[u]),x))
                for base in choices:
                    direction=-1 if base<left else 1
                    for step in range(len(units)+1):
                        x=base+direction*column_step*step
                        if valid(u,x,centers):
                            centers[u]=x; changed=True; break
                    else:
                        continue
                    break
        if not changed:
            break
    # Spread movable, single-use roots around a merge instead of assigning
    # a geometrically reversed port to disguise same-side crowding.
    for target in sorted(nodes):
        feeds=incoming[target]
        if len(feeds)<3:
            continue
        tx=centers[find(target)]
        for sign in (-1,1):
            same=[i for i in feeds if (centers[find(i)]-tx)*sign>sizes[target]['width']/2]
            for i in same[1:]:
                u=find(i)
                if incoming[i] or len(outgoing[i])!=1 or len(units[u])!=1 or nodes[i].get('scope'):
                    continue
                for k in range(1,len(units)+1):
                    x=tx-sign*column_step*k
                    scope_hit=False
                    for members in scopes.values():
                        if not members: continue
                        top=min(ys[layers[j]] for j in members)-48
                        end=max(ys[layers[j]]+sizes[j]['height'] for j in members)+24
                        left=min(centers[find(j)]-sizes[j]['width']/2 for j in members)-24
                        right=max(centers[find(j)]+sizes[j]['width']/2 for j in members)+24
                        if ys[layers[i]]<end and ys[layers[i]]+sizes[i]['height']>top and x+sizes[i]['width']/2>left and x-sizes[i]['width']/2<right:
                            scope_hit=True
                    if not scope_hit and valid(u,x,centers):
                        centers[u]=x; break
    boxes={i:{'x':round(centers[find(i)]-sizes[i]['width']/2),'y':ys[layers[i]],'width':sizes[i]['width'],'height':sizes[i]['height']} for i in nodes}
    # Single-use roots leave below the tallest card in their row; a diagonal
    # native fallback must not immediately run behind a taller neighbour.
    for i in nodes:
        if not incoming[i]:
            row_height=max(sizes[j]['height'] for j in nodes if layers[j]==layers[i])
            boxes[i]['y']+=row_height-sizes[i]['height']
    return boxes, layers, spine

def refine_routes(model, analysis, boxes, layers):
    """Bounded horizontal search using the actual routed paths as its score."""
    from .routing import analyze, prepare
    import copy

    nodes = analysis['nodes']
    edges = [e for e in model['edges'] if e['source'] in boxes and e['target'] in boxes]
    column_step = max(448, max(box['width'] for box in boxes.values()) + NODE_GAP)

    parent = {i:i for i in nodes}
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def join(a,b):
        parent[find(a)] = find(b)
    for nid, node in nodes.items():
        if node['type'] in ('COMBINE', 'TRANSFORM') and analysis['outgoing'][nid]:
            join(nid, analysis['outgoing'][nid][0])
    units = defaultdict(list)
    for nid in sorted(nodes):
        units[find(nid)].append(nid)

    def canvas(bs):
        result = {'metadata':{}, 'nodes':[], 'edges':[]}
        for nid, box in bs.items():
            shape = 'circle' if nodes[nid]['type'] in ('COMBINE', 'CASE') else 'rectangle'
            result['nodes'].append({'id':nid, 'type':'text', **box,
                                    'styleAttributes':{'shape':shape}})
        result['edges'] = [{'id':e['id'], 'fromNode':e['source'], 'toNode':e['target']}
                           for e in edges]
        return prepare(result)

    def valid(bs):
        values = list(bs.items())
        for index, (_, a) in enumerate(values):
            for _, b in values[index+1:]:
                if (a['x'] < b['x']+b['width']+NODE_GAP and a['x']+a['width']+NODE_GAP > b['x']
                        and a['y'] < b['y']+b['height']+NODE_GAP and a['y']+a['height']+NODE_GAP > b['y']):
                    return False
        grouped_members = [list(scope_members(model, scope['id'])) for scope in model.get('scopes', [])]
        grouped_members.append([nid for nid,node in nodes.items()
                               if node['type']=='INTUITION' or not node.get('strict',True)])
        for members in grouped_members:
            if not members:
                continue
            left = min(bs[i]['x'] for i in members)-24
            right = max(bs[i]['x']+bs[i]['width'] for i in members)+24
            top = min(bs[i]['y'] for i in members)-48
            bottom = max(bs[i]['y']+bs[i]['height'] for i in members)+24
            for nid, box in bs.items():
                if nid in members:
                    continue
                if (box['x'] < right and box['x']+box['width'] > left
                        and box['y'] < bottom and box['y']+box['height'] > top):
                    return False
        return True

    def route_stats(bs):
        report = analyze(canvas(bs))
        intersections = sum(c['code'] == 'ROUTE-NODE-INTERSECTION' for c in report['conflicts'])
        shared = [c for c in report['conflicts'] if c['code'] == 'ROUTE-SHARED-SEGMENT']
        node_clearance = sum(c['code'] == 'ROUTE-NODE-CLEARANCE' for c in report['conflicts'])
        parallel_clearance = sum(c['code'] == 'ROUTE-PARALLEL-CLEARANCE' for c in report['conflicts'])
        route_shape = sum(c['code'] in ('ROUTE-LOCAL-NOT-DOWNWARD', 'ROUTE-TURN-CLEARANCE')
                          for c in report['conflicts'])
        by_id = {e['id']:e for e in edges}
        horizontal, maximum, path_total = 0, 0, 0
        combine_centers = defaultdict(list)
        for edge_id, points in report['paths'].items():
            length = sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(points, points[1:]))
            path_total += length
            edge = by_id[edge_id]
            if nodes[edge['target']]['type'] == 'COMBINE':
                dx = sum(abs(a[0]-b[0]) for a,b in zip(points, points[1:]))
                horizontal += dx
                maximum = max(maximum, dx)
                combine_centers[edge['target']].append(bs[edge['source']]['x']+bs[edge['source']]['width']/2)
        balance = 0
        for target, sources in combine_centers.items():
            center = bs[target]['x']+bs[target]['width']/2
            balance += abs(center-sum(sources)/len(sources))
        width = max(b['x']+b['width'] for b in bs.values())-min(b['x'] for b in bs.values())
        score = (intersections, len(shared), node_clearance, parallel_clearance, route_shape,
                 round(sum(c['length'] for c in shared),2),
                 round(maximum,2), round(horizontal,2), round(balance,2),
                 round(path_total,2), len(report['crossings']), round(width,2))
        return score, report

    current = copy.deepcopy(boxes)
    current_score, report = route_stats(current)
    roots = sorted(units, key=lambda u:(0 if any(i in {c.get('node') for c in report['conflicts']} for i in units[u]) else 1,
                                       min(layers[i] for i in units[u]), u))
    for _ in range(12):
        changed = False
        for unit in roots:
            members = units[unit]
            old_center = current[members[0]]['x']+current[members[0]]['width']/2
            neighbor_centers = []
            for nid in members:
                for other in analysis['incoming'][nid]+analysis['outgoing'][nid]:
                    neighbor_centers.append(current[other]['x']+current[other]['width']/2)
            anchors = {old_center, 0}
            anchors.update(neighbor_centers)
            anchors.update(old_center+(column_step/2)*k for k in range(-8,9))
            best, best_score = None, current_score
            for center in sorted(anchors, key=lambda x:(abs(x-old_center), x)):
                delta = round(center-old_center)
                if not delta:
                    continue
                trial = copy.deepcopy(current)
                for nid in members:
                    trial[nid]['x'] += delta
                if not valid(trial):
                    continue
                candidate, _ = route_stats(trial)
                if candidate < best_score:
                    best, best_score = trial, candidate
            if best is not None:
                current, current_score, changed = best, best_score, True
        if not changed:
            break
    return current

def sides(model, boxes, layers):
    incoming=defaultdict(list)
    result={}
    byid={n['id']:n for n in model['nodes']}
    center=lambda i: boxes[i]['x']+boxes[i]['width']/2
    for e in model['edges']:
        incoming[e['target']].append(e)
        result[e['id']]=['bottom','top']
    for target, edges in incoming.items():
        if byid[target]['type']=='COMBINE' and 1 < len(edges) <= 3:
            ordered=sorted(edges,key=lambda e:(center(e['source']),e['id']))
            if len(ordered) == 3:
                for e,side in zip(ordered,['left','top','right']):result[e['id']][1]=side
            else:
                tc=center(target); top=min(ordered,key=lambda e:(abs(center(e['source'])-tc),e['id']))
                other=next(e for e in ordered if e is not top)
                result[top['id']][1]='top'
                result[other['id']][1]='left' if center(other['source'])<=tc else 'right'
        elif len(edges)>1:
            for e in edges:
                sx=center(e['source']); t=boxes[target]
                result[e['id']][1]='left' if sx<t['x'] else 'right' if sx>t['x']+t['width'] else 'top'
    load=Counter()
    for e in sorted(model['edges'],key=lambda e:e['id']):
        s,t=e['source'],e['target']
        if byid[s]['type'] in ('COMBINE', 'TRANSFORM'):
            result[e['id']]=['bottom','top']
        elif layers[t]-layers[s]>2:
            lo=min(b['x'] for b in boxes.values())-48
            hi=max(b['x']+b['width'] for b in boxes.values())+48
            side=min(('left','right'),key=lambda side:(load[side],abs(center(s)-(lo if side=='left' else hi))+abs(center(t)-(lo if side=='left' else hi)),side))
            result[e['id']][0]=side
            load[side]+=1
    outgoing=defaultdict(list)
    for e in model['edges']:
        outgoing[e['source']].append(e)
    for source, edges in outgoing.items():
        if len(edges)<2 or byid[source]['type'] in ('COMBINE', 'TRANSFORM'):
            continue
        main=min(edges,key=lambda e:(abs(center(e['target'])-center(source)),e['id']))
        for e in edges:
            if e!=main:
                result[e['id']][0]='left' if center(e['target'])<center(source) else 'right'
    # Fixed center ports have capacity one. For current fan-out, allocate distinct
    # left/bottom/right exits in target order instead of allowing long-edge
    # heuristics to reuse one physical port.
    for source, edges in outgoing.items():
        if byid[source]['type'] in ('COMBINE', 'TRANSFORM') or len(edges) <= 1:
            continue
        if len(edges) <= 3:
            ordered=sorted(edges,key=lambda e:(center(e['target']),e['id']))
            ports={2:['left','right'],3:['left','bottom','right']}[len(ordered)]
            for e,side in zip(ordered,ports):result[e['id']][0]=side
    return result

def metrics(model, canvas, routing=None):
    boxes={n['id']:n for n in canvas['nodes'] if n['id'] in {i['id'] for i in model['nodes']}}
    rows={}; row=-1; end=float('-inf')
    for n in sorted(boxes.values(),key=lambda n:(n['y'],n['id'])):
        if n['y']>=end: row+=1
        rows[n['id']]=row; end=max(end,n['y']+n['height'])
    gaps=[]; long=0; offsets=[]
    node_types={n['id']:n['type'] for n in model['nodes']}
    proof_edges={e['id']:e for e in model['edges']}
    combine_dx=[]; combine_centers=defaultdict(list); combine_long=0
    if routing is None:
        from .routing import analyze
        routing=analyze(canvas)
    for e in canvas['edges']:
        s,t=boxes[e['fromNode']],boxes[e['toNode']]
        gaps.append(t['y']-s['y']-s['height'])
        long+=rows[t['id']]-rows[s['id']]>2
        if next(n for n in model['nodes'] if n['id']==s['id'])['type']=='COMBINE':
            offsets.append(abs(s['x']+s['width']/2-t['x']-t['width']/2))
        proof=proof_edges[e['id']]
        if node_types[proof['target']]=='COMBINE':
            points=routing['paths'][e['id']]
            dx=sum(abs(a[0]-b[0]) for a,b in zip(points,points[1:]))
            combine_dx.append(dx)
            combine_centers[proof['target']].append(s['x']+s['width']/2)
            combine_long += rows[t['id']]-rows[s['id']]>2
    balance=sum(abs(boxes[target]['x']+boxes[target]['width']/2-sum(values)/len(values))
                for target,values in combine_centers.items())
    return {'max_vertical_gap':max(gaps,default=0),'long_edges':long,
            'combine_result_offset':sum(offsets),
            'combine_feed_horizontal_total':round(sum(combine_dx),2),
            'combine_feed_horizontal_max':round(max(combine_dx,default=0),2),
            'combine_cluster_balance_offset':round(balance,2),'combine_long_reuse_count':combine_long}

def combine_feed_details(model, canvas, routing=None):
    """Per-edge diagnostics emitted only by an explicit layout report."""
    if routing is None:
        from .routing import analyze
        routing=analyze(canvas)
    boxes={n['id']:n for n in canvas['nodes'] if n['id'] in {i['id'] for i in model['nodes']}}
    types={n['id']:n['type'] for n in model['nodes']}
    outgoing=Counter(e['source'] for e in model['edges'])
    paired={nid for e in model['edges'] if types[e['source']] in ('COMBINE','TRANSFORM')
            for nid in (e['source'],e['target'])}
    rows={y:i for i,y in enumerate(sorted({n['y'] for n in boxes.values()}))}
    details=[]
    for edge in model['edges']:
        if types[edge['target']]!='COMBINE' or edge['id'] not in routing['paths']:
            continue
        points=routing['paths'][edge['id']]
        dx=sum(abs(a[0]-b[0]) for a,b in zip(points,points[1:]))
        dy=sum(abs(a[1]-b[1]) for a,b in zip(points,points[1:]))
        details.append({'edge':edge['id'],'source':edge['source'],'target':edge['target'],
                        'dx':round(dx,2),'dy':round(dy,2),'path_length':round(dx+dy,2),
                        'long_reuse':outgoing[edge['source']]>1 and rows[boxes[edge['target']]['y']]-rows[boxes[edge['source']]['y']]>2,
                        'independent_unit':edge['source'] not in paired})
    return details

def diagnostic_svg(canvas):
    ns=canvas['nodes']; byid={n['id']:n for n in ns}
    x=min(n['x'] for n in ns)-40; y=min(n['y'] for n in ns)-80
    w=max(n['x']+n['width'] for n in ns)-x+40; h=max(n['y']+n['height'] for n in ns)-y+40
    from .routing import analyze
    routes=analyze(canvas)
    bad={c['edge'] for c in routes['conflicts']}|{c['other_edge'] for c in routes['conflicts'] if 'other_edge' in c}
    out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}">', '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill="#567"/></marker></defs>',f'<text x="{x+20}" y="{y+30}" font-size="22">Downward orthogonal zero/two-bend paths</text>']
    for e in canvas['edges']:
        p=routes['paths'].get(e['id'])
        if not p: continue
        d='M '+' L '.join(f'{a} {b}' for a,b in p)
        color='#d22' if e['id'] in bad else '#567'
        out.append(f'<path d="{d}" stroke="{color}" stroke-width="2" fill="none" marker-end="url(#arrow)"/><text x="{p[0][0]+8}" y="{p[0][1]+24}" font-size="14">{escape(e["id"])}</text>')
    for n in ns:
        if n.get('styleAttributes',{}).get('shape')=='circle':
            out.append(f'<circle cx="{n["x"]+n["width"]/2}" cy="{n["y"]+n["height"]/2}" r="{n["width"]/2}" fill="#fff5d7" stroke="#456"/>')
        else:
            out.append(f'<rect x="{n["x"]}" y="{n["y"]}" width="{n["width"]}" height="{n["height"]}" fill="{"none" if n["type"]=="group" else "#eef5ff"}" stroke="#456"/>')
        out.append(f'<text x="{n["x"]+12}" y="{n["y"]+28}" font-size="22">{escape(n["id"])}</text>')
    for conflict in routes['conflicts']:
        a,b=conflict.get('segment',conflict.get('segments',[[[0,0],[0,0]]])[0])
        out.append(f'<circle cx="{(a[0]+b[0])/2}" cy="{(a[1]+b[1])/2}" r="10" fill="red"/><title>{escape(str(conflict))}</title>')
    return '\n'.join(out+['</svg>'])
