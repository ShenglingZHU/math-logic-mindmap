"""Compile authored expression/application rows into one continuous MathJax chain."""
from __future__ import annotations
import re

from .common import Invalid
from .readability import resolve


def tex_text(text):
    escaped = {'\\': r'\textbackslash{}', '{': r'\{', '}': r'\}', '&': r'\&',
               '%': r'\%', '#': r'\#', '_': r'\_', '$': r'\$', '^': r'\textasciicircum{}', '~': r'\textasciitilde{}'}
    return ''.join(escaped.get(c, c) for c in text)


def math_content(block):
    if block['kind'] == 'formula':
        return block['latex']
    # Preserve inline mathematics in a textual condition, escape only prose.
    parts = re.split(r'(\$[^$]+\$)', block['text'])
    return ''.join(p[1:-1] if p.startswith('$') and p.endswith('$') else r'\text{' + tex_text(p) + '}' for p in parts if p)


def validate_chain(node, nodes):
    chain = node.get('derivation_chain')
    if not chain:
        raise Invalid(f'CHAIN {node["id"]}: an operation node without a continuous main chain cannot be built or released')
    pool = {b.get('id'): b for b in node['derivation']}
    if None in pool or len(pool) != len(node['derivation']):
        raise Invalid(f'CHAIN-BLOCK {node["id"]}: every content block must have a unique ID')
    rows = chain['rows']
    ids = [r['step_id'] for r in rows]
    if len(ids) != len(set(ids)) or any(i not in pool for i in ids):
        raise Invalid('CHAIN-STEP: main-chain steps are duplicated or missing')
    if rows[0]['kind'] != 'expression' or rows[-1]['kind'] != 'expression':
        raise Invalid('CHAIN-ENDS: the main chain must start and end with expressions')
    uses = {u['step_id']: u for u in node['input_usage']}
    starts = [u for u in node['input_usage'] if u['mode'] == 'start']
    if len(starts) != 1:
        raise Invalid('CHAIN-START: exactly one real starting input is required')
    start = starts[0]
    if ids[0] != start['step_id']:
        raise Invalid('CHAIN-START: the first row must be the actual content of the starting input')
    output_latex = node.get('combine_output_latex', node.get('transform_output_latex'))
    allowed_inputs = node.get('combine_inputs', [node.get('transform_input')])
    if pool[ids[-1]].get('latex') != output_latex:
        raise Invalid('CHAIN-RESULT: the final main-chain expression must match the formal output and successor')
    auxiliaries = {a['id']: a for a in chain.get('auxiliaries', [])}
    if len(auxiliaries) != len(chain.get('auxiliaries', [])):
        raise Invalid('CHAIN-AUX: auxiliary calculation IDs are duplicated')
    auxiliary_blocks = set()
    used_aux = set()
    for a in auxiliaries.values():
        if (not a['steps'] or any(i not in pool for i in a['steps'])
                or a['result_ref'] != a['steps'][-1]
                or any(pool[i]['kind'] != 'formula' for i in a['steps'])):
            raise Invalid('CHAIN-AUX: an auxiliary calculation must consist entirely of formulas and end with its declared formula result')
        if auxiliary_blocks.intersection(a['steps']):
            raise Invalid('CHAIN-AUX: an auxiliary step cannot belong to multiple auxiliary calculations')
        auxiliary_blocks.update(a['steps'])
    symbols = set()
    previous_left = None
    for index, row in enumerate(rows):
        block = pool[row['step_id']]
        symbols.update(s['symbol_latex'] for s in block.get('symbols', []))
        if row['kind'] == 'expression':
            latex = math_content(block)
            split = row['split_at']
            if not 0 <= split <= len(latex):
                raise Invalid('CHAIN-ALIGN: the alignment position is outside the expression')
            left = latex[:split]
            if split and not re.match(r'(?:=|<|>|\\(?:leq?|geq?|neq?|equiv|Rightarrow|Longrightarrow|Leftrightarrow|Longleftrightarrow|implies|iff|in|subseteq|subset|sim|approx)(?![A-Za-z]))', latex[split:]):
                raise Invalid('CHAIN-ALIGN: a nonzero anchor must precede a real relation symbol')
            # A continuation may hide only an unchanged left-hand expression.
            if row.get('continuation') and (not left or left != previous_left):
                raise Invalid('CHAIN-CONTINUATION: a changed left-hand expression cannot be omitted')
            if left.count('{') != left.count('}') or ('\\begin' in left) or ('\\end' in left):
                raise Invalid('CHAIN-ALIGN: an alignment anchor cannot split a command argument or environment')
            previous_left = left
            if row['step_id'] in uses and uses[row['step_id']]['mode'] != 'start':
                raise Invalid('CHAIN-INPUT: every additional input must be introduced by a justification-application row')
        else:
            if index == 0 or index == len(rows)-1 or rows[index-1]['kind'] != 'expression' or rows[index+1]['kind'] != 'expression' or row['next_step'] != rows[index+1]['step_id']:
                raise Invalid('CHAIN-APPLICATION: a justification must bind the adjacent before and after expressions')
            count = sum(k in row for k in ('source', 'auxiliary_ref', 'external'))
            if count != 1:
                raise Invalid('CHAIN-BASIS: specify exactly one input source, auxiliary result, or external rule')
            if 'source' in row:
                src = row['source']
                if src['node'] not in allowed_inputs:
                    raise Invalid('CHAIN-SOURCE: a source must be delivered by a current direct input')
                source = resolve(nodes, src['node'], src['formula_ref'])
                if any(source.get(k) != block.get(k) for k in ('kind', 'latex', 'symbols', 'text')):
                    raise Invalid('CHAIN-SOURCE: the boxed justification does not match its source content')
            if 'auxiliary_ref' in row:
                aid = row['auxiliary_ref']
                if aid not in auxiliaries or row['step_id'] != auxiliaries[aid]['result_ref']:
                    raise Invalid('CHAIN-AUX: the referenced auxiliary result is missing or inconsistent')
                if aid in used_aux:
                    raise Invalid('CHAIN-AUX: each auxiliary calculation must be introduced by exactly one justification row')
                used_aux.add(aid)
            if row['step_id'] in uses:
                u = uses[row['step_id']]
                if row.get('source') != {'node': u['node'], 'formula_ref': u['formula_ref']}:
                    raise Invalid('CHAIN-INPUT: an input-usage record is not bound to an actual justification row')
    if not set(uses).issubset(ids):
        raise Invalid('CHAIN-INPUT: every input-usage record must appear in the main chain')
    if used_aux != set(auxiliaries):
        raise Invalid('CHAIN-AUX: an auxiliary result must return to explicit use in the main chain')
    annotations = chain.get('explanations', [])
    if any(i not in pool or pool[i]['kind'] != 'prose' for i in annotations):
        raise Invalid('CHAIN-NOTE: a step explanation outside the chain must reference a prose block')
    ordinary_rows = set(ids) - {a['result_ref'] for a in auxiliaries.values()}
    if ordinary_rows & auxiliary_blocks or ordinary_rows & set(annotations) or auxiliary_blocks & set(annotations):
        raise Invalid('CHAIN-COVERAGE: a content block cannot belong to multiple rendering regions')
    if set(ids) | auxiliary_blocks | set(annotations) != set(pool):
        raise Invalid('CHAIN-COVERAGE: one or more content blocks are not rendered')
    for aid in used_aux:
        for block_id in auxiliaries[aid]['steps']:
            symbols.update(s['symbol_latex'] for s in pool[block_id].get('symbols', []))
    actual = [s['symbol_latex'] for s in chain['symbols']]
    if len(actual) != len(set(actual)) or set(actual) != symbols:
        raise Invalid('CHAIN-SYMBOLS: one main-chain symbol table must cover every row and justification exactly')


def require_chains(model):
    nodes = {n['id']: n for n in model['nodes']}
    for node in nodes.values():
        if node['type'] in ('COMBINE', 'TRANSFORM'):
            validate_chain(node, nodes)


def compile_chain(node, language='zh-CN'):
    chain = node['derivation_chain']
    pool = {b['id']: b for b in node['derivation']}
    lines = []
    for row in chain['rows']:
        latex = math_content(pool[row['step_id']])
        if row['kind'] == 'expression':
            split = row['split_at']
            lines.append(('' if row.get('continuation') else latex[:split]) + '&' + latex[split:])
        else:
            # The invisible copy sizes the single down arrow to the full basis box.
            title = row['name']
            if 'source' in row:
                title += ('，' if language == 'zh-CN' else ', ') + row['source']['node']
            name = r'(\text{' + tex_text(title) + '})'
            if 'auxiliary_ref' in row:
                aux = next(a for a in chain.get('auxiliaries', []) if a['id'] == row['auxiliary_ref'])
                body = r'\\[0.6em]'.join(r'&\displaystyle ' + math_content(pool[i]) for i in aux['steps'])
                basis = r'\boxed{\begin{aligned}' + body + r'\\[0.4em]&' + name + r'\end{aligned}}'
            elif len(latex) <= 110 and r'\begin' not in latex and r'\\' not in latex:
                basis = r'\boxed{\displaystyle ' + latex + r'\qquad ' + name + '}'
            else:
                basis = r'\boxed{\begin{aligned}&\begin{aligned}' + latex + r'\end{aligned}\\[0.4em]&' + name + r'\end{aligned}}'
            arrow = r'\left.\vphantom{' + basis + r'}\rule{0pt}{3em}\right\downarrow'
            lines.append('&' + arrow + r'\qquad ' + basis)
    out = r'\begin{aligned}' + '\n'
    for i, line in enumerate(lines):
        if i:
            gap = '2.5em' if chain['rows'][i]['kind'] == 'apply' or chain['rows'][i-1]['kind'] == 'apply' else '0.8em'
            out += r'\\[' + gap + ']\n'
        out += line + '\n'
    return {'kind':'formula','latex':out + r'\end{aligned}','symbols':chain['symbols']}
