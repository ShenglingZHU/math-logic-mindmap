"""Node-owned reading context. No graph edges or mathematics are invented here."""
from __future__ import annotations

import re

from .common import Invalid
from .i18n import reserved_headings, reserved_prefixes

RESERVED = reserved_headings()
RESERVED_PREFIXES = reserved_prefixes()

_RAW_TEX = re.compile(r'\\[A-Za-z]+')
_RAW_SCRIPT = re.compile(
    r'(?<![A-Za-z0-9_])(?:[A-Za-z0-9]|[\u0370-\u03ff])'
    r'(?:_(?:\{[^{}\s]+\}|[A-Za-z0-9])|\^(?:\{[^{}\s]+\}|[A-Za-z0-9]))'
)
_RAW_UNICODE_MATH = re.compile(
    r'[\u0370-\u03ff\u2070\u00b9\u00b2\u00b3\u2074-\u2079'
    r'\u2080-\u2089\u2115\u211a\u211d\u2124\u2200\u2202\u2203'
    r'\u220f\u2211\u221a\u221e]'
)
_OPERAND = r'(?:[A-Za-z]|[0-9]+|[\u0370-\u03ff\u2115\u211a\u211d\u2124])(?:_[A-Za-z0-9])?'
_LETTER_OPERAND = r'(?:[A-Za-z]|[\u0370-\u03ff])(?:_[A-Za-z0-9])?'
_RAW_CALL = re.compile(
    r'(?<![A-Za-z0-9_])(?:[A-Za-z]|sin|cos|tan|log|ln|exp)\(\s*'
    + _OPERAND + r'(?:\s*[+*/-]\s*' + _OPERAND + r')*\s*\)'
)
_RAW_ARITHMETIC = re.compile(
    r'(?<![A-Za-z0-9_])(?:'
    + _LETTER_OPERAND + r'\s*[+*/-]\s*' + _OPERAND
    + r'|[0-9]+\s*[+*/-]\s*' + _LETTER_OPERAND
    + r')(?![A-Za-z0-9_])'
)
_RAW_ABSOLUTE = re.compile(r'(?<![|A-Za-z0-9_])\|' + _OPERAND + r'\|(?![|A-Za-z0-9_])')
_RAW_PRIME = re.compile(r"(?<![A-Za-z0-9_])" + _LETTER_OPERAND + r"'(?![A-Za-z0-9_'])")
_RAW_RELATION = re.compile(_OPERAND + r'\s*(?:=|<|>|\u2208|\u2209|\u2264|\u2265|\u2260|\u2248|\u2192|\u21d2|\u21d4|\u2282|\u2286)\s*' + _OPERAND)
_AMBIGUOUS_OPERATOR = re.compile(r'[\u2208\u2209\u2264\u2265\u2260\u2248\u2192\u21d2\u21d4\u2282\u2286]')
_AMBIGUOUS_FUNCTION = re.compile(
    r'(?<![A-Za-z0-9_])(?:sin|cos|tan|log|ln|exp)\s+'
    + _LETTER_OPERAND + r'(?![A-Za-z0-9_])'
)
_ISOLATED_ASCII = re.compile(r'(?<![A-Za-z0-9_])([A-Za-z])(?![A-Za-z0-9_])')


def _symbol_text_fields(rows, location):
    for index, row in enumerate(rows or []):
        for key in ('definition_role', 'range_unit', 'interpretation'):
            yield f'{location}/{index}/{key}', row[key]


def markdown_fields(model):
    """Yield authored strings rendered as Markdown, never structural identifiers or raw TeX."""
    theorem = model['theorem']
    yield 'model/theorem/title', theorem['title']
    for key in ('assumptions', 'missing_assumptions', 'open_obligations'):
        for index, value in enumerate(theorem.get(key, [])):
            yield f'model/theorem/{key}/{index}', value
    if theorem.get('counterexample'):
        yield 'model/theorem/counterexample', theorem['counterexample']
    for key, value in model['context'].items():
        yield f'model/context/{key}', value
    yield from _symbol_text_fields(model.get('symbols', []), 'model/symbols')

    for index, stage in enumerate(model['proof_flow']):
        yield f'model/proof_flow/{index}/summary', stage['summary']
    for index, branch in enumerate(model['presentation'].get('branches', [])):
        yield f'model/presentation/branches/{index}/title', branch['title']
    for index, review in enumerate(model['presentation'].get('granularity_reviews', [])):
        yield f'model/presentation/granularity_reviews/{index}/reason', review['reason']

    for node_index, node in enumerate(model['nodes']):
        base = f'model/nodes/{node_index}'
        yield f'{base}/short_role', node['short_role']
        for key in ('conditions', 'condition_checks'):
            for index, value in enumerate(node.get(key, [])):
                yield f'{base}/{key}/{index}', value
        if node.get('navigation'):
            for key in ('role', 'motivation'):
                yield f'{base}/navigation/{key}', node['navigation'][key]
        for key in ('combine_motivation', 'combine_method', 'transform_motivation', 'transform_method'):
            if node.get(key):
                yield f'{base}/{key}', node[key]
        for key in ('input_review', 'input_context'):
            for index, row in enumerate(node.get(key, [])):
                yield f'{base}/{key}/{index}/contribution', row['contribution']
        if node.get('output_handoff'):
            for key in ('explanation', 'downstream_use'):
                yield f'{base}/output_handoff/{key}', node['output_handoff'][key]
        for section_index, section in enumerate(node.get('sections', [])):
            section_base = f'{base}/sections/{section_index}'
            yield f'{section_base}/heading', section['heading']
            for block_index, block in enumerate(section['blocks']):
                block_base = f'{section_base}/blocks/{block_index}'
                if block['kind'] == 'prose':
                    yield f'{block_base}/text', block['text']
                else:
                    yield from _symbol_text_fields(block['symbols'], f'{block_base}/symbols')
        for block_index, block in enumerate(node.get('derivation', [])):
            block_base = f'{base}/derivation/{block_index}'
            if block['kind'] == 'prose':
                yield f'{block_base}/text', block['text']
            else:
                yield from _symbol_text_fields(block['symbols'], f'{block_base}/symbols')
        if node.get('derivation_chain'):
            yield from _symbol_text_fields(node['derivation_chain']['symbols'], f'{base}/derivation_chain/symbols')

    for edge_index, edge in enumerate(model['edges']):
        detail = edge.get('detail')
        if not detail:
            continue
        base = f'model/edges/{edge_index}/detail'
        for key in ('summary', 'source_contribution', 'target_gain', 'role_in_proof'):
            yield f'{base}/{key}', detail[key]
        for key in ('transition_steps', 'conditions', 'condition_checks'):
            for index, value in enumerate(detail.get(key, [])):
                yield f'{base}/{key}/{index}', value
        for section_index, section in enumerate(detail.get('sections', [])):
            section_base = f'{base}/sections/{section_index}'
            yield f'{section_base}/heading', section['heading']
            for block_index, block in enumerate(section['blocks']):
                block_base = f'{section_base}/blocks/{block_index}'
                if block['kind'] == 'prose':
                    yield f'{block_base}/text', block['text']
                else:
                    yield from _symbol_text_fields(block['symbols'], f'{block_base}/symbols')


def plain_text_fields(model):
    """Yield labels rendered as literal text or inside TeX text boxes."""
    for index, stage in enumerate(model['proof_flow']):
        yield f'model/proof_flow/{index}/title', stage['title']
    for index, scope in enumerate(model.get('scopes', [])):
        yield f'model/scopes/{index}/title', scope['title']
    for index, edge in enumerate(model['edges']):
        if edge.get('label_text'):
            yield f'model/edges/{index}/label_text', edge['label_text']
    for node_index, node in enumerate(model['nodes']):
        yield f'model/nodes/{node_index}/title', node['title']
        for row_index, row in enumerate(node.get('derivation_chain', {}).get('rows', [])):
            if row.get('name'):
                yield f'model/nodes/{node_index}/derivation_chain/rows/{row_index}/name', row['name']


def _unescaped_dollar(text, start=0):
    for index in range(start, len(text)):
        if text[index] != '$':
            continue
        backslashes = 0
        cursor = index - 1
        while cursor >= 0 and text[cursor] == '\\':
            backslashes += 1
            cursor -= 1
        if backslashes % 2 == 0:
            return index
    return -1


def _markdown_prose(text, location):
    text = re.sub(r'`[^`\n]*`', '', text)
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', '', text)
    text = re.sub(r'\[([^\]]+)\]\((?:https?://|mailto:)[^)]+\)', r'\1', text)
    text = re.sub(r'https?://[^\s)]+', '', text)
    prose, cursor = [], 0
    while True:
        opening = _unescaped_dollar(text, cursor)
        if opening < 0:
            prose.append(text[cursor:])
            break
        prose.append(text[cursor:opening])
        closing = _unescaped_dollar(text, opening + 1)
        if closing < 0:
            raise Invalid(f'MATH-INLINE-DELIMITER {location}: inline mathematics is missing its closing $; escape an ordinary dollar sign as \\$')
        content = text[opening + 1:closing]
        if not content or content[0].isspace() or content[-1].isspace():
            raise Invalid(f'MATH-INLINE-DELIMITER {location}: $...$ content cannot be empty or have leading/trailing whitespace; escape an ordinary dollar sign as \\$')
        if any(ord(char) < 32 or ord(char) == 127 for char in content):
            raise Invalid(f'MATH-INLINE-CONTROL {location}: inline mathematics cannot contain a line break or control character')
        cursor = closing + 1
    return ''.join(prose)


def _raw_math(prose):
    for pattern in (_RAW_TEX, _RAW_SCRIPT, _RAW_UNICODE_MATH, _RAW_CALL,
                    _RAW_ARITHMETIC, _RAW_ABSOLUTE, _RAW_PRIME, _RAW_RELATION):
        match = pattern.search(prose)
        if match:
            return match.group(0)
    return None


def validate_inline_math(model):
    warnings = []
    language = model.get('presentation', {}).get('language', 'zh-CN')
    for location, text in markdown_fields(model):
        prose = _markdown_prose(text, location)
        token = _raw_math(prose)
        if token:
            raise Invalid(f'MATH-INLINE {location}: {token} must be enclosed in $...$; use backticks for a code identifier')
        function = _AMBIGUOUS_FUNCTION.search(prose)
        if function:
            warnings.append(f'MATH-INLINE-RISK {location}: review bare function notation {function.group(0)}')
        ambiguous = _AMBIGUOUS_OPERATOR.search(prose)
        if ambiguous:
            warnings.append(f'MATH-INLINE-RISK {location}: review bare symbol {ambiguous.group(0)}')
        if language == 'zh-CN':
            isolated = _ISOLATED_ASCII.search(prose)
            if isolated:
                warnings.append(f'MATH-INLINE-RISK {location}: review isolated letter {isolated.group(1)}')
    for location, text in plain_text_fields(model):
        if _unescaped_dollar(text) >= 0:
            raise Invalid(f'MATH-PLAIN-TEXT {location}: a plain-text field cannot use $...$; rewrite it in natural language')
        token = _raw_math(text)
        if token:
            raise Invalid(f'MATH-PLAIN-TEXT {location}: a plain-text field cannot contain formula {token}; rewrite it in natural language')
        if language == 'zh-CN':
            isolated = _ISOLATED_ASCII.search(text)
            if isolated:
                warnings.append(f'MATH-INLINE-RISK {location}: review isolated letter {isolated.group(1)}')
    return warnings


def formula_blocks(node):
    return [b for s in node['sections'] for b in s['blocks'] if b['kind'] == 'formula']


def content_blocks(node):
    return [b for s in node['sections'] for b in s['blocks']]


def resolve(nodes, nid, ref):
    if nid not in nodes:
        raise Invalid(f'READING-REF: node {nid} does not exist')
    node = nodes[nid]
    if ref == 'core':
        latex = node.get('formula_latex') or node.get('combine_output_latex') or node.get('transform_output_latex')
        if not latex:
            prose = next((b for b in content_blocks(node) if b['kind'] == 'prose'), None)
            if prose:
                return prose
            raise Invalid(f'READING-REF {nid}: missing a core formula or body proposition')
        candidates = formula_blocks(node) + [b for b in node.get('derivation', []) if b['kind'] == 'formula']
        symbols = next((b['symbols'] for b in candidates if b['latex'] == latex), None)
        if symbols is None:
            raise Invalid(f'READING-REF {nid}: the core formula lacks an identical local symbol table')
        return {'kind': 'formula', 'latex': latex, 'symbols': symbols}
    found = [b for b in content_blocks(node) if b.get('id') == ref]
    if len(found) != 1:
        raise Invalid(f'READING-REF {nid}/{ref}: the formula reference is missing or not unique')
    return found[0]


def inline_formula(latex):
    return len(latex) <= 100 and not any(x in latex for x in ('\n', r'\\', r'\begin', r'\boxed'))


def validate_readability(model):
    nodes = {n['id']: n for n in model['nodes']}
    if not model.get('proof_flow') or any(not n.get('navigation') for n in nodes.values()):
        raise Invalid('READABILITY: proof_flow, node navigation, and combination input-usage records are incomplete')
    stages = model['proof_flow']
    if len({s['id'] for s in stages}) != len(stages) or len({s['title'] for s in stages}) != len(stages):
        raise Invalid('READING-FLOW: stage IDs or titles are duplicated')
    if any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', s['id']) or any(c in s['title'] for c in '\n#|[]') for s in stages):
        raise Invalid('READING-FLOW: a stage ID or title cannot produce a stable navigation anchor')
    memberships = [nid for s in stages for nid in s['nodes']]
    if sorted(memberships) != sorted(nodes):
        raise Invalid('READING-FLOW: stages must cover every node exactly once')
    for n in nodes.values():
        nid = n['id']
        nav = n['navigation']
        if not all(isinstance(nav.get(k), str) and nav[k].strip() for k in ('stage', 'role', 'motivation')):
            raise Invalid(f'READING-NAV {nid}: navigation fields are incomplete')
        if not any(s['id'] == nav['stage'] and nid in s['nodes'] for s in stages):
            raise Invalid(f'READING-NAV {nid}: stage membership is incorrect')
        headings = [s['heading'] for s in n['sections']]
        if len(headings) != len(set(headings)) or RESERVED.intersection(headings) or any(h.startswith(RESERVED_PREFIXES) for h in headings):
            raise Invalid(f'READING-HEADING {nid}: a heading conflicts with a reserved heading or is duplicated')
        ids = [b['id'] for b in content_blocks(n) if 'id' in b]
        if len(ids) != len(set(ids)) or 'core' in ids:
            raise Invalid(f'READING-REF {nid}: a formula ID is duplicated or uses reserved ID core')
        resolve(nodes, nid, n.get('reading_ref', 'core'))
        if n['type'] not in ('COMBINE', 'TRANSFORM'):
            continue
        required = ('input_review', 'input_usage', 'output_handoff')
        if n['type'] == 'COMBINE':
            required += ('start_input',)
        required += (('combine_motivation', 'combine_method') if n['type'] == 'COMBINE' else ('transform_motivation', 'transform_method'))
        if any(not n.get(k) for k in required):
            raise Invalid(f'READABILITY {nid}: operation-node reading fields are missing')
        pred = n['combine_inputs'] if n['type'] == 'COMBINE' else [n['transform_input']]
        reviews = n['input_review']
        uses = n['input_usage']
        if sorted(r['node'] for r in reviews) != sorted(pred) or sorted(u['node'] for u in uses) != sorted(pred):
            raise Invalid(f'READING-INPUT {nid}: review and usage records must each cover every input exactly once')
        steps = {b.get('id'): b for b in n['derivation'] if b.get('id')}
        if len(steps) != len([b for b in n['derivation'] if b.get('id')]):
            raise Invalid(f'READING-STEP {nid}: step IDs are duplicated')
        starts = [u for u in uses if u['mode'] == 'start']
        expected_start = n.get('start_input', n.get('transform_input'))
        if len(starts) != 1 or starts[0]['node'] != expected_start:
            raise Invalid(f'READING-START {nid}: exactly one real starting input is required')
        formulas = [b for b in n['derivation'] if b['kind'] == 'formula']
        if len({u['step_id'] for u in uses}) != len(uses):
            raise Invalid(f'READING-USE {nid}: each input must bind a distinct step')
        start_step = steps.get(starts[0]['step_id'])
        if not start_step or (start_step['kind'] == 'formula' and formulas[0].get('id') != starts[0]['step_id']) or (start_step['kind'] == 'prose' and any(b['kind'] == 'formula' for b in n['derivation'][:n['derivation'].index(start_step)])):
            raise Invalid(f'READING-START {nid}: the first formula must be the starting input')
        for row in reviews:
            resolve(nodes, row['node'], row['formula_ref'])
            if not row['contribution'].strip():
                raise Invalid(f'READING-INPUT {nid}: an input contribution is empty')
        for use in uses:
            source = resolve(nodes, use['node'], use['formula_ref'])
            step = steps.get(use['step_id'])
            if not step or step['kind'] != source['kind'] or any(step.get(k) != source.get(k) for k in ('latex', 'symbols', 'text')):
                raise Invalid(f'READING-USE {nid}/{use["node"]}: the step does not match its source formula or symbol table')
            if step['kind'] == 'prose' and use['mode'] == 'basis':
                raise Invalid(f'READING-USE {nid}: a prose proposition must use start or condition and explain its verification role nearby')
            if use['mode'] not in ('start', 'basis', 'condition'):
                raise Invalid(f'READING-USE {nid}: unknown usage mode')
            if step is formulas[-1]:
                raise Invalid(f'READING-USE {nid}: a result block cannot replace an input-usage step')
    for e in model['edges']:
        if e['detail_mode'] != 'STRUCTURAL_ONLY' or nodes[e['source']]['type'] in ('COMBINE', 'TRANSFORM') or nodes[e['target']]['type'] in ('COMBINE', 'TRANSFORM'):
            continue
        rows = nodes[e['target']].get('input_context', [])
        if len([r for r in rows if r['edge_id'] == e['id'] and r['contribution'].strip()]) != 1:
            raise Invalid(f'READING-RELATION {e["id"]}: the receiving node lacks exactly one input context')
    for n in nodes.values():
        rows = n.get('input_context', [])
        valid = {e['id'] for e in model['edges'] if e['target'] == n['id'] and e['detail_mode'] == 'STRUCTURAL_ONLY' and nodes[e['source']]['type'] not in ('COMBINE', 'TRANSFORM') and n['type'] not in ('COMBINE', 'TRANSFORM')}
        if sorted(r['edge_id'] for r in rows) != sorted(valid):
            raise Invalid(f'READING-RELATION {n["id"]}: input contexts are duplicated or do not belong to this node')
    # Semantic TeX bars must be authored, never mechanically changed by Markdown escaping.
    def inspect(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and (k in ('latex', 'formula_latex', 'symbol_latex') or re.search(r'\$[^$]*\|[^$]*\$', v)) and '|' in v:
                    raise Invalid('TABLE-BAR: mathematical bars must use lvert/rvert/lVert/rVert/mid')
                inspect(v)
        elif isinstance(obj, list):
            for v in obj:
                inspect(v)
    inspect(model)
    return validate_inline_math(model)
