from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict, deque
from pathlib import Path

from .common import CONTEXT, ID, Invalid, digest, read_json, slug_value
from .config import DEFAULT_COLORS, model_language, normalize_config

TYPES = {"ASSUMPTION", "DEFINITION", "KNOWN_RESULT", "CONSTRUCTION", "LOCAL_INTRODUCTION", "CASE",
         "HYPOTHESIS_LOCAL", "DERIVATION", "LEMMA", "COMBINE", "TRANSFORM", "CONTRADICTION",
         "BOUND", "EXISTENCE_WITNESS", "TARGET", "INTUITION"}
COLORS = DEFAULT_COLORS
EDGE_COLORS = {"EDGE_DETAIL": "#4A90C4", "STRUCTURAL_ONLY": "#6F7782"}
CARD_WIDTHS = (400, 480, 560, 640, 720, 800)
SYMBOL_COLUMN_WIDTH_PX = 140


def units(text):
    return sum(1 if unicodedata.east_asian_width(c) in "WF" else 0.5 for c in text)


def _latex_width_em(latex):
    """Estimate one MathJax line without turning TeX source length into width."""
    spacing = {"quad": 1.0, "qquad": 2.0, ",": .167, ";": .278,
               ":": .222, " ": .333, "!": -.167}
    symbols = {
        "sum": .9, "prod": .9, "int": .65, "sqrt": .65, "gcd": 1.7, "bot": .8,
        "le": .8, "leq": .8, "ge": .8, "geq": .8, "neq": .8,
        "ne": .8, "equiv": .8, "in": .75, "notin": .85,
        "subset": .85, "subseteq": .9, "cup": .8, "cap": .8,
        "to": .9, "Rightarrow": 1.05, "iff": 1.05,
        "forall": .8, "exists": .8, "land": .8, "lor": .8,
        "cdot": .65, "times": .75, "mid": .45, "pm": .8,
        "infty": .75, "infinity": .75, "partial": .65,
        "lambda": .65, "alpha": .65, "beta": .65, "gamma": .65,
        "delta": .65, "sigma": .65, "Sigma": .75, "mu": .65,
        "nu": .65, "theta": .65, "epsilon": .65, "varepsilon": .65,
        "varnothing": .75, "dots": .9, "ldots": .9, "cdots": .9,
        "lvert": .35, "rvert": .35, "lVert": .45, "rVert": .45,
    }
    wrappers = {"mathbb", "mathcal", "mathrm", "operatorname", "text",
                "hat", "bar", "overline", "underbrace", "overbrace",
                "overset", "underset"}

    def group(pos):
        if pos >= len(latex) or latex[pos] != "{":
            atom, end = parse(pos, stop_at_atom=True)
            return atom, end
        value, end = parse(pos + 1, stop="}")
        return value, min(end + 1, len(latex))

    def parse(pos, stop=None, stop_at_atom=False):
        atoms = []
        while pos < len(latex) and latex[pos] != stop:
            char = latex[pos]
            if char in "_^":
                script, pos = group(pos + 1)
                scaled = max(0.0, script * .7)
                if atoms:
                    atoms[-1] = max(atoms[-1], scaled)
                else:
                    atoms.append(scaled)
                continue
            if char == "{":
                value, pos = group(pos)
                atoms.append(value)
            elif char == "\\":
                match = re.match(r"\\([A-Za-z]+|.)", latex[pos:])
                if not match:
                    pos += 1
                    continue
                command = match.group(1)
                pos += len(match.group(0))
                if command in spacing:
                    atoms.append(spacing[command])
                elif command in ("left", "right", "displaystyle"):
                    continue
                elif command in ("frac", "dfrac", "tfrac"):
                    numerator, pos = group(pos)
                    denominator, pos = group(pos)
                    atoms.append(max(numerator, denominator) + .4)
                elif command == "sqrt":
                    value, pos = group(pos)
                    atoms.append(value + .6)
                elif command in wrappers:
                    value, pos = group(pos)
                    atoms.append(value if command != "text" else value)
                else:
                    atoms.append(symbols.get(command, .8))
            else:
                if unicodedata.east_asian_width(char) in "WF":
                    width = 1.0
                elif char.isalnum():
                    width = .6
                elif char in "=<>+-":
                    width = .75
                elif char in "()[]|":
                    width = .4
                elif char in ",.;:":
                    width = .3
                elif char.isspace():
                    width = .25
                else:
                    width = .6
                atoms.append(width)
                pos += 1
            if stop_at_atom and atoms:
                break
        return max(0.0, sum(atoms)), pos

    return parse(0)[0]


def _formula_width(formula):
    rows = formula.split(r"\\") if formula else []
    # The scanner measures serial atoms. MathJax's italic spacing and script
    # boxes make the rendered result wider; measured MathJax samples calibrate
    # these two deliberately simple safety factors.
    return max((_latex_width_em(re.sub(r"\\(?:begin|end)\{aligned\}", "", row).replace("&", ""))
                 * 16 * (1.55 if "_" in row or "^" in row else 1.3)
                for row in rows), default=0.0)


def card_formula(node):
    mode = node.get("card_formula_display", "full")
    if mode not in ("full", "summary"):
        raise Invalid(f"CARD-FORMULA {node['id']}: unknown display mode")
    return (node.get("formula_latex") or "") if mode == "full" else ""


def _has_top_level_symbol_separator(latex):
    """Reject unambiguous notation lists without pretending to parse all of TeX."""
    stack = []
    pairs = {"(": ")", "[": "]", "{": "}"}
    command_pairs = {
        "langle": "rangle",
        "lceil": "rceil",
        "lfloor": "rfloor",
        "lvert": "rvert",
        "lVert": "rVert",
    }
    spacing_commands = {"quad", "qquad", "enspace", "space"}
    i = 0
    while i < len(latex):
        char = latex[i]
        if char == "\\":
            if i + 1 < len(latex) and latex[i + 1] in "{}":
                escaped = latex[i + 1]
                if escaped == "{":
                    stack.append("\\}")
                elif stack and stack[-1] == "\\}":
                    stack.pop()
                i += 2
                continue
            command = re.match(r"\\([A-Za-z]+|.)", latex[i:])
            if command:
                token = command.group(1)
                end = i + len(command.group(0))
                if token in command_pairs:
                    stack.append("\\" + command_pairs[token])
                    i = end
                    continue
                if stack and stack[-1] == "\\" + token:
                    stack.pop()
                    i = end
                    continue
                if not stack and (token in spacing_commands or token in (" ", ",", ";", ":")):
                    if latex[:i].strip() and latex[end:].strip():
                        return True
                i = end
                continue
        if char in pairs:
            stack.append(pairs[char])
        elif stack and char == stack[-1]:
            stack.pop()
        elif not stack and char in ",，;；":
            if latex[:i].strip() and latex[i + 1:].strip():
                return True
        i += 1
    return False


def _symbol_related_to_latex(symbol, latex):
    """Conservative ownership hint: uncertainty is a warning, never rejection."""
    compact_symbol = re.sub(r"\s+", "", symbol).replace(r"\left", "").replace(r"\right", "")
    compact_latex = re.sub(r"\s+", "", latex).replace(r"\left", "").replace(r"\right", "")
    if compact_symbol and compact_symbol in compact_latex:
        return True
    commands = [c for c in re.findall(r"\\([A-Za-z]+)", symbol)
                if c not in {"left", "right", "mathbb", "mathcal", "mathrm", "operatorname", "text"}]
    if commands:
        return any(("\\" + command) in latex for command in commands)
    match = re.search(r"[A-Za-z]", re.sub(r"\\[A-Za-z]+", "", symbol))
    if not match:
        return True
    atom = match.group(0)
    return bool(re.search(rf"(?<![A-Za-z\\]){re.escape(atom)}(?![A-Za-z])", latex))


def _check_symbol_rows(rows, *, warnings, location, latex=None):
    for row in rows:
        symbol = row["symbol_latex"]
        if _has_top_level_symbol_separator(symbol):
            raise Invalid(f"SYMBOL-ROW-ATOMIC {location}: each row may explain only one notation item: {symbol}")
        estimated = _latex_width_em(symbol) * 15 * 1.55 + 16
        if estimated > SYMBOL_COLUMN_WIDTH_PX:
            warnings.append(f"SYMBOL-WIDTH-RISK {location}/{symbol}: estimated width exceeds the nominal first-column width; inspect it in Obsidian")
        if latex is not None and not _symbol_related_to_latex(symbol, latex):
            warnings.append(f"SYMBOL-OWNERSHIP-RISK {location}/{symbol}: cannot confirm that this notation belongs to the current formula; review it manually")


def estimate(node, config=None):
    """A deliberately conservative risk estimate, never a rendered fit assertion."""
    if node["type"] == "CASE":
        needed = max(180, 80 + max(0, len(node["id"]) - 6) * 14,
                     80 + units(node["title"]) * 14,
                     80 + max(0, len(node.get("case_branches", [])) - 1) * 40)
        diameter = math.ceil(needed / 8) * 8
        return {"width": diameter, "height": diameter, "risk": []}
    if node["type"] == "COMBINE":
        if len(node["id"]) > 6 or not node["id"].isascii():
            raise Invalid(f"CARD-BUDGET {node['id']}: a COMBINE ID may contain at most 6 ASCII characters")
        return {"width": 180, "height": 180, "risk": []}
    if node["type"] == "TRANSFORM":
        if len(node["id"]) > 6 or not node["id"].isascii():
            raise Invalid(f"CARD-BUDGET {node['id']}: a TRANSFORM ID may contain at most 6 ASCII characters")
        if units(node["title"]) > 6 or "\n" in node["title"]:
            raise Invalid(f"CARD-BUDGET {node['id']}: a TRANSFORM operation title may contain at most 6 full-width units and no line break")
        return {"width": 240, "height": 180, "risk": []}
    title, role = node["title"], node["short_role"]
    formula = card_formula(node)
    risks = []
    if units(title) > 18 or "\n" in title:
        raise Invalid(f"CARD-BUDGET {node['id']}: title exceeds 18 full-width units or one line")
    if units(role) > 36 or "\n" in role:
        raise Invalid(f"CARD-BUDGET {node['id']}: role summary exceeds 36 full-width units or one paragraph")
    lines = formula.count(r"\\") + 1 if formula else 0
    if len(formula) > 240:
        raise Invalid(f"CARD-BUDGET {node['id']}: displayed formula is too long; use the summary card mode")
    if "$" in formula or re.search(r"(?<!\\)\\[\[\]]", formula):
        raise Invalid(f"MATH-DELIMITER {node['id']}: formula_latex must not contain display delimiters")
    if re.search(r"\\(?:overbrace|underbrace|overset|underset|newcommand|def)\b", formula):
        risks.append("Complex formula; inspect its dimensions in the real environment")
    commands = re.findall(r"\\([A-Za-z]+)", formula)
    known = set("frac dfrac tfrac sqrt gcd bot sum prod int lim le leq ge geq in notin subset subseteq cup cap varnothing lambda alpha beta gamma delta sigma Sigma mu nu theta epsilon varepsilon forall exists quad qquad mathbb mathcal mathrm operatorname text left right lvert rvert lVert rVert mid cdot times dots ldots cdots displaystyle to Rightarrow iff neg land lor pm infinity infty neq ne equiv partial hat bar overline underbrace begin end".split())
    if set(commands) - known:
        risks.append("Contains commands not recognized by the estimator: " + ", ".join(sorted(set(commands) - known)))
    formula_width = _formula_width(formula)
    required_width = formula_width * 1.1 + 40
    if config is not None:
        from .i18n import catalog
        words = catalog(config)
        navigation_units = units(" · ".join((words["details"], words["in"], words["out"])))
        required_width = max(required_width, navigation_units * 16 + 40)
    width = next((candidate for candidate in CARD_WIDTHS if candidate >= required_width), CARD_WIDTHS[-1])
    if required_width > CARD_WIDTHS[-1]:
        if lines == 1 and re.search(r"(?:\\quad|,)", formula):
            risks.append("CARD-WRAP-SUGGESTION: the single-line formula is estimated above 800px; the author may split it into two lines at a natural boundary")
        risks.append("FORMULA-WIDTH-RISK: the formula is estimated above 800px; inspect the actual MathJax output")
    formula_h = lines * 38 + min(64, formula.count(r"\frac") * 16 + formula.count(r"\sum") * 12)
    if "^" in formula or "_" in formula:
        formula_h += 12
    content_width = width - 40
    height = math.ceil((42 + 30 + math.ceil(max(units(role), 1) * 16 / content_width) * 25.6
                        + formula_h + 58 + 40) * 1.25 / 8) * 8
    if height > 480:
        raise Invalid(f"CARD-BUDGET {node['id']}: estimated height {height}>480; simplify the card")
    return {"width": width, "height": max(280, height), "risk": risks}


def model_identity(model):
    return digest(model)


def validate(model):
    try:
        from jsonschema import Draft202012Validator
    except ImportError as exc:
        raise Invalid("SCHEMA UNKNOWN: install the project dependency jsonschema and retry") from exc
    schema = read_json(Path(__file__).parent / "schemas" / "proof-model.schema.json")
    errors = sorted(Draft202012Validator(schema).iter_errors(model), key=lambda e: str(list(e.path)))
    if errors:
        raise Invalid("SCHEMA: " + "; ".join(f"{list(e.path)} {e.message}" for e in errors[:12]))
    slug_value(model["slug"])
    model_language(model)
    nodes, edges = model["nodes"], model["edges"]
    by_id = {n["id"]: n for n in nodes}
    ids = [x["id"] for x in nodes + edges]
    if len({i.casefold() for i in ids}) != len(ids) or any(not ID.fullmatch(i) for i in ids):
        raise Invalid("ID: node and edge IDs must be globally unique case-insensitively and contain no hyphen")
    if any(n["id"].startswith(("E", "UI", "G")) for n in nodes):
        raise Invalid("ID: prefixes E, UI, and G are reserved for edges, interface elements, and groups")
    if any(not e["id"].startswith("E") for e in edges):
        raise Invalid("ID: edge IDs must use the E prefix")
    target = model["target_id"]
    if target not in by_id or by_id[target]["type"] != "TARGET":
        raise Invalid("TARGET: target_id must reference a TARGET node")
    if sum(n["type"] == "TARGET" for n in nodes) != 1:
        raise Invalid("TARGET: every model must have exactly one target")
    strict = {n["id"] for n in nodes if n.get("strict", True) and n["type"] != "INTUITION"}
    incoming, outgoing = defaultdict(list), defaultdict(list)
    warnings = []
    pairs = set()
    for e in edges:
        s, t = e["source"], e["target"]
        if s not in by_id or t not in by_id or s == t or (s, t) in pairs:
            raise Invalid(f"EDGE {e['id']}: missing endpoint, self-loop, or duplicate dependency")
        pairs.add((s, t))
        incoming[t].append(s)
        outgoing[s].append(t)
        if s not in strict and t in strict:
            raise Invalid(f"STRICT {e['id']}: a non-proof node cannot support a strict conclusion")
        if e["relation"] == "CASE_BRANCH" and by_id[s]["type"] != "CASE":
            raise Invalid(f"CASE-BRANCH {e['id']}: branches must start at CASE")
        if e["relation"] == "FEEDS_CASE" and by_id[t]["type"] != "CASE":
            raise Invalid(f"CASE {e['id']}: FEEDS_CASE must enter CASE")
        detail = e["detail_mode"] == "EDGE_DETAIL"
        if detail:
            if len(e["detail"]["conditions"]) != len(e["detail"]["condition_checks"]):
                raise Invalid(f"CONDITIONS {e['id']}: every condition must have a verification")
            if not e.get("label_text", "").strip() or e.get("label_latex"):
                raise Invalid(f"LABEL {e['id']}: use one nonempty plain-text label_text")
            if any(c in e["label_text"] for c in ("\n", "$", "[[", "\\")) or units(e["label_text"]) > 24:
                raise Invalid(f"LABEL {e['id']}: a label must be short plain text without formulas or links")
        elif e.get("label_text") or e.get("label_latex") or e.get("detail"):
            raise Invalid(f"STRUCTURAL_ONLY {e['id']}: a structural edge cannot have a label or independent detail")
        if s in strict and t in strict and e.get("display_mode") != "FLOW":
            raise Invalid(f"REFERENCE {e['id']}: a strict dependency must be visible FLOW")
        scope_entry = by_id[t]["type"] == "HYPOTHESIS_LOCAL" or e["relation"] == "OPENS_SCOPE"
        if s in strict and t in strict and all(by_id[i]["type"] not in ("COMBINE", "TRANSFORM", "CASE") for i in (s, t)) and not detail and not scope_entry:
            raise Invalid(f"EDGE_DETAIL {e['id']}: an ordinary single-input transition must be explained")
        if e["relation"] == "DISCHARGES" and not detail:
            raise Invalid(f"DISCHARGES {e['id']}: discharge must be explained")
    # Check all edges for cycles; strict subgraph must also be a DAG.
    indeg = {i: len(incoming[i]) for i in by_id}
    queue = deque(sorted(i for i in by_id if not indeg[i]))
    order, ranks = [], {}
    while queue:
        i = queue.popleft()
        order.append(i)
        ranks[i] = max((ranks[p] + 1 for p in incoming[i]), default=0)
        for child in outgoing[i]:
            indeg[child] -= 1
            if not indeg[child]:
                queue.append(child)
    if len(order) != len(nodes):
        raise Invalid("DAG: directed cycle")
    for n in nodes:
        nid = n["id"]
        if n["type"] not in TYPES or nid == "START" or n["title"].upper() == "START":
            raise Invalid(f"NODE {nid}: unsupported type or decorative START")
        pred = [i for i in incoming[nid] if i in strict]
        succ = [i for i in outgoing[nid] if i in strict]
        if n["type"] == "COMBINE":
            if len(pred) < 2 or len(succ) != 1 or not n.get("derivation"):
                raise Invalid(f"COMBINE {nid}: requires at least 2 strict inputs, 1 strict output, and a derivation")
            if set(n.get("combine_inputs", [])) != set(pred):
                raise Invalid(f"COMBINE {nid}: combine_inputs do not match actual inputs")
            if n.get("combine_output_latex") != by_id[succ[0]].get("formula_latex"):
                raise Invalid(f"COMBINE {nid}: output must match the successor core formula")
            final_formulas = [b["latex"] for b in n["derivation"] if b["kind"] == "formula"]
            if not final_formulas or final_formulas[-1] != n["combine_output_latex"]:
                raise Invalid(f"COMBINE {nid}: the final derivation formula block must explicitly output the successor core formula; an expanded form may precede it")
            if any(e["relation"] != "FEEDS_COMBINE" for e in edges if e["target"] == nid):
                raise Invalid(f"COMBINE {nid}: input relations must be FEEDS_COMBINE")
            if any(e["relation"] != "COMBINE_PRODUCES" for e in edges if e["source"] == nid):
                raise Invalid(f"COMBINE {nid}: output relation must be COMBINE_PRODUCES")
            if by_id[succ[0]]["type"] != "TARGET" and not by_id[succ[0]].get("result", False):
                raise Invalid(f"COMBINE {nid}: successor must be a result:true conclusion or TARGET")
            if n.get("combine_reason") not in {"premise_synthesis", "theorem_application", "branch_merge", "case_reconciliation", "independent_results", "induction"}:
                raise Invalid(f"COMBINE {nid}: missing a valid combine_reason")
        elif n["type"] == "CASE":
            if len(pred) != 1 or len(succ) != len(n.get("case_branches", [])):
                raise Invalid(f"CASE {nid}: input or branch count is invalid")
        elif n["type"] == "LOCAL_INTRODUCTION":
            if len(pred) != 1 or len(succ) != 1 or not n.get("bindings"):
                raise Invalid(f"LOCAL_INTRODUCTION {nid}: requires one input, one output, and bound symbols")
        elif n["type"] in ("CONSTRUCTION", "EXISTENCE_WITNESS"):
            if len(pred) != 1 or len(succ) != 1:
                raise Invalid(f"{n['type']} {nid}: requires exactly one strict input and output")
        elif n["type"] == "TRANSFORM":
            required = ("transform_input", "transform_output_latex", "transform_motivation", "transform_method",
                        "input_review", "input_usage", "derivation", "derivation_chain", "output_handoff")
            if len(pred) != 1 or len(succ) != 1 or any(not n.get(k) for k in required):
                raise Invalid(f"TRANSFORM {nid}: requires one strict input, one strict output, and complete derivation fields")
            if n["transform_input"] != pred[0]:
                raise Invalid(f"TRANSFORM {nid}: transform_input must equal the sole actual predecessor")
            if n["transform_output_latex"] != by_id[succ[0]].get("formula_latex"):
                raise Invalid(f"TRANSFORM {nid}: output and successor core formula must use the same string")
            formulas = [b["latex"] for b in n["derivation"] if b["kind"] == "formula"]
            if not formulas or formulas[-1] != n["transform_output_latex"]:
                raise Invalid(f"TRANSFORM {nid}: final derivation expression must match the formal output")
            if any(e["relation"] != "FEEDS_TRANSFORM" or e["detail_mode"] != "STRUCTURAL_ONLY" for e in edges if e["target"] == nid):
                raise Invalid(f"TRANSFORM {nid}: input edge must be unlabeled FEEDS_TRANSFORM")
            if any(e["relation"] != "TRANSFORM_PRODUCES" or e["detail_mode"] != "STRUCTURAL_ONLY" for e in edges if e["source"] == nid):
                raise Invalid(f"TRANSFORM {nid}: output edge must be unlabeled TRANSFORM_PRODUCES")
        elif nid in strict and len(pred) > 1:
            raise Invalid(f"COMBINE {nid}: a multi-input result lacks an independent COMBINE")
        if n["type"] in ("COMBINE", "TRANSFORM", "CASE") and any(by_id[i]["type"] in ("COMBINE", "TRANSFORM", "CASE") for i in pred + succ):
            raise Invalid(f"OPERATION-ADJACENCY {nid}: operation nodes cannot be directly adjacent")
        if nid in strict and not pred and n["type"] not in ("ASSUMPTION", "DEFINITION", "KNOWN_RESULT", "HYPOTHESIS_LOCAL"):
            raise Invalid(f"ROOT {nid}: a strict root must be an assumption, definition, or known result")
        if n["type"] in ("ASSUMPTION", "DEFINITION", "KNOWN_RESULT") and pred:
            raise Invalid(f"ROOT {nid}: a root type cannot have a strict predecessor")
        if n["type"] == "HYPOTHESIS_LOCAL" and not n.get("scope"):
            raise Invalid(f"SCOPE {nid}: a local assumption must have a scope")
        if n["type"] == "HYPOTHESIS_LOCAL" and len(pred) > 1:
            raise Invalid(f"SCOPE {nid}: a local assumption has multiple strict inputs")
        if len(n.get("conditions", [])) != len(n.get("condition_checks", [])):
            raise Invalid(f"CONDITIONS {nid}: every condition must have one verification")
        size = estimate(n)
        warnings.extend(f"{nid}: {w}" for w in size["risk"])
        conjunction = r"与|和|、|\band\b" + (r"|\bet\b" if model_language(model) == "fr" else "")
        if re.search(conjunction, n["title"], re.IGNORECASE):
            warnings.append(f"ATOMIC {nid}: a coordinated title must justify its indivisibility in mathematical review")
    status = model["theorem"]["status"]
    if status == "proved" and (model["theorem"]["proof_standard"] in ("heuristic", "counterexample") or target not in strict):
        raise Invalid("STATUS: an intuition, counterexample, or non-strict target cannot be marked proved")
    if status in ("proved", "refuted"):
        reaches = {target}
        todo = [target]
        while todo:
            for p in incoming[todo.pop()]:
                if p not in reaches:
                    reaches.add(p)
                    todo.append(p)
        if strict - reaches:
            raise Invalid("REACHABILITY: strict nodes do not support the target: " + ",".join(sorted(strict - reaches)))
        flow_incoming = defaultdict(list)
        for e in edges:
            if e.get("display_mode") == "FLOW":
                flow_incoming[e["target"]].append(e["source"])
        reaches_flow, todo = {target}, [target]
        while todo:
            for p in flow_incoming[todo.pop()]:
                if p not in reaches_flow:
                    reaches_flow.add(p); todo.append(p)
        if strict - reaches_flow:
            raise Invalid("FLOW-REACHABILITY: strict nodes do not reach the target along pure FLOW paths: " + ",".join(sorted(strict - reaches_flow)))
    else:
        if not model["theorem"].get("open_obligations"):
            raise Invalid("STATUS: an incomplete model must list open_obligations")
        if any(e["relation"] == "ESTABLISHES_TARGET" for e in edges):
            raise Invalid("STATUS: an incomplete proposition cannot use ESTABLISHES_TARGET")
    if status == "refuted" and not model["theorem"].get("counterexample"):
        raise Invalid("STATUS: refuted requires an explicit counterexample")
    if status == "needs_assumption" and not model["theorem"].get("missing_assumptions"):
        raise Invalid("STATUS: needs_assumption requires explicit missing conditions")
    # Every display block owns its symbol rows; raw display delimiters in prose are forbidden.
    _check_symbol_rows(model["symbols"], warnings=warnings, location="global")

    def inspect(obj, location="model"):
        if isinstance(obj, dict):
            if obj.get("kind") == "prose" and ("$$" in obj["text"] or re.search(r"(?<!\\)\\[\[\]]", obj["text"])):
                raise Invalid("SYMBOL-TABLE: a display formula must use a formula block and cannot be hidden in prose")
            if obj.get("kind") == "formula":
                if "$" in obj["latex"] or not obj["symbols"]:
                    raise Invalid("FORMULA: LaTeX has no delimiters and must have a local symbol table")
                _check_symbol_rows(obj["symbols"], warnings=warnings,
                                   location=location, latex=obj["latex"])
                for row in obj["symbols"]:
                    if "|" in row["symbol_latex"]:
                        raise Invalid("TABLE-BAR: mathematical bars must use lvert/rvert/lVert/rVert/mid")
            for key, value in obj.items():
                inspect(value, f"{location}/{key}")
        elif isinstance(obj, list):
            for index, value in enumerate(obj):
                inspect(value, f"{location}/{index}")
        elif isinstance(obj, str) and ("$$" in obj or "<script" in obj or re.search(r"(?<!\\)\\[\[\]]", obj)):
            raise Invalid("CONTENT: a display formula must use a formula block's delimiter-free latex field and cannot embed executable scripts")
    inspect(model)
    for n in nodes:
        if n.get("derivation_chain"):
            chain_latex = "\n".join(b["latex"] for b in n.get("derivation", []) if b.get("kind") == "formula")
            _check_symbol_rows(n["derivation_chain"]["symbols"], warnings=warnings,
                               location=f'{n["id"]}/derivation_chain', latex=chain_latex)
    scopes = {s["id"] for s in model.get("scopes", [])}
    if len(scopes) != len(model.get("scopes", [])) or any(not ID.fullmatch(i) for i in scopes) or any(n.get("scope") not in scopes for n in nodes if n.get("scope")):
        raise Invalid("SCOPE: scope IDs are duplicated or a reference does not exist")
    from .scope_semantics import validate_scopes
    quantifier_order = validate_scopes(model, by_id, incoming, outgoing, order, warnings)
    if 'proof_flow' in model:
        from .readability import validate_readability
        warnings.extend(validate_readability(model))
    from .chains import validate_chain
    for n in nodes:
        if 'derivation_chain' in n:
            if n['type'] not in ('COMBINE', 'TRANSFORM'):
                raise Invalid('CHAIN-TYPE: a structured main chain is only valid for COMBINE/TRANSFORM')
            validate_chain(n, by_id)
    from .human import validate_human
    warnings.extend(validate_human(model, by_id, incoming, outgoing))
    return {"nodes": by_id, "incoming": incoming, "outgoing": outgoing,
            "order": order, "ranks": ranks, "warnings": warnings,
            "quantifier_order": quantifier_order}


def node_color_role(node):
    if node["type"] == "KNOWN_RESULT" or node.get("external", False):
        return "external"
    if node["type"] in ("COMBINE", "CASE"):
        return "combine"
    if node["type"] == "TRANSFORM":
        return "transform"
    if node["type"] == "TARGET":
        return "target"
    if node.get("result", False):
        return "result"
    if node["type"] == "INTUITION" or not node.get("strict", True):
        return None
    if node["type"] in ("ASSUMPTION", "LOCAL_INTRODUCTION"):
        return "given"
    return None


def node_color(node, config=None):
    role = node_color_role(node)
    return normalize_config(config)["node_colors"][role] if role else None
