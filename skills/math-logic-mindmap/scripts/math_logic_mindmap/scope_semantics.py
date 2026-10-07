"""Lexical scope, bound-symbol, case, and induction checks for Proof models."""
from .common import Invalid


def scope_members(model, scope_id):
    """Return node IDs in a scope or any of its child scopes."""
    scopes = {s["id"]: s for s in model.get("scopes", [])}

    def within(current):
        seen = set()
        while current and current not in seen:
            if current == scope_id:
                return True
            seen.add(current)
            current = scopes.get(current, {}).get("parent_scope")
        return False

    return {n["id"] for n in model["nodes"] if within(n.get("scope"))}


def validate_scopes(model, nodes, incoming, outgoing, order, warnings=None):
    warnings = [] if warnings is None else warnings
    scopes = {s["id"]: s for s in model.get("scopes", [])}
    edges = {e["id"]: e for e in model["edges"]}

    def parents(scope):
        seen = set()
        while scope:
            if scope not in scopes or scope in seen:
                raise Invalid(f"SCOPE-PARENT {scope}: missing parent or cycle")
            seen.add(scope)
            yield scope
            scope = scopes[scope].get("parent_scope")

    def contains(outer, inner):
        if outer is None:
            return True
        return outer in set(parents(inner)) if inner else False

    def reaches(source, target):
        todo, seen = [source], set()
        while todo:
            current = todo.pop()
            if current == target:
                return True
            if current not in seen:
                seen.add(current)
                todo.extend(outgoing[current])
        return False

    for scope in scopes.values():
        sid, opener, closer = scope["id"], scope["opened_by"], scope["closed_by"]
        parent = scope.get("parent_scope")
        list(parents(sid))
        if opener not in nodes or closer not in nodes and closer not in edges:
            raise Invalid(f"SCOPE-PAIR {sid}: opener or closer does not exist")
        opened = nodes[opener]
        members = scope_members(model, sid)
        opening_edge = edges.get(scope.get("opening_edge"))
        if opened["type"] == "LOCAL_INTRODUCTION":
            if opened.get("scope") != parent or not opening_edge or opening_edge["source"] != opener or opening_edge["relation"] != "OPENS_SCOPE" or nodes[opening_edge["target"]].get("scope") != sid:
                raise Invalid(f"SCOPE-OPEN {sid}: introduction must open its child scope on its sole output")
            source_edges = [e for e in model["edges"] if e["target"] == opener]
            if len(source_edges) != 1 or source_edges[0]["detail_mode"] != "EDGE_DETAIL":
                raise Invalid(f"SCOPE-OPEN {sid}: introduction requires one explained value source")
            first = opening_edge["target"]
        elif opened["type"] == "HYPOTHESIS_LOCAL":
            if opened.get("scope") != sid or opening_edge or incoming[opener]:
                raise Invalid(f"SCOPE-OPEN {sid}: opening local hypothesis must be a strict root")
            first = opener
        else:
            raise Invalid(f"SCOPE-OPEN {sid}: opener must be a local introduction or local hypothesis")
        def nested_hypothesis_root_member(nid):
            for child in scopes.values():
                if child["id"] == sid or not contains(sid, child["id"]):
                    continue
                root = child["opened_by"]
                if (nodes[root]["type"] == "HYPOTHESIS_LOCAL" and not incoming[root]
                        and not child.get("opening_edge") and reaches(root, nid)):
                    return True
            return False

        if not members or any(not reaches(first, nid) and not nested_hypothesis_root_member(nid) for nid in members):
            raise Invalid(f"SCOPE-MEMBERS {sid}: every member must descend from the opening")
        if closer in edges:
            e = edges[closer]
            if e["relation"] != "DISCHARGES" or e.get("closes_scope") != sid or e["source"] not in members or nodes[e["target"]].get("scope") != parent:
                raise Invalid(f"SCOPE-CLOSE {sid}: discharge must cross into the parent scope")
            discharged = set(e.get("discharges", []))
        else:
            combine = nodes[closer]
            if combine["type"] != "COMBINE" or not combine.get("paired_case") or combine.get("scope") != parent:
                raise Invalid(f"SCOPE-CLOSE {sid}: only a paired case COMBINE may close a branch scope")
            rows = [row for row in combine.get("scope_closures", []) if row["scope"] == sid]
            if len(rows) != 1:
                raise Invalid(f"SCOPE-CLOSE {sid}: case COMBINE must record its closure once")
            discharged = set(rows[0]["discharges"])
            for hid in rows[0]["discharges"]:
                if hid not in nodes or nodes[hid]["type"] != "HYPOTHESIS_LOCAL" or hid not in members or not any(reaches(hid, source) for source in incoming[closer]):
                    raise Invalid(f"SCOPE-CLOSE {sid}: case discharge has an unrelated assumption")
        local_hypotheses = {nid for nid in members if nodes[nid]["type"] == "HYPOTHESIS_LOCAL" and nodes[nid].get("scope") == sid}
        if discharged != local_hypotheses:
            raise Invalid(f"SCOPE-CLOSE {sid}: every direct local hypothesis must be discharged exactly once")
        for e in model["edges"]:
            if e["source"] in members and e["target"] not in members:
                if not nodes[e["target"]].get("strict", True) or nodes[e["target"]]["type"] == "INTUITION":
                    continue
                if e["id"] == closer or (closer in nodes and e["target"] == closer and e["relation"] == "FEEDS_COMBINE"):
                    continue
                raise Invalid(f"SCOPE-LEAK {e['id']}: a local result leaves {sid} before its closure")

    for e in model["edges"]:
        if e["relation"] == "OPENS_SCOPE":
            if e["detail_mode"] != "STRUCTURAL_ONLY" or sum(s.get("opening_edge") == e["id"] for s in scopes.values()) != 1:
                raise Invalid(f"SCOPE-OPEN {e['id']}: opening edge must belong to exactly one scope")
        if e["relation"] != "DISCHARGES":
            continue
        sid, rule = e.get("closes_scope"), e.get("discharge_rule")
        if sid not in scopes or scopes[sid]["closed_by"] != e["id"] or not rule:
            raise Invalid(f"DISCHARGES {e['id']}: rule and matching scope closure are required")
        hypotheses = e.get("discharges", [])
        opened = nodes[scopes[sid]["opened_by"]]
        mode = opened.get("introduction_mode")
        generalizes = e.get("generalizes", [])
        if mode == "witness" and rule != "existential_elimination":
            raise Invalid(f"WITNESS-CLOSE {e['id']}: witness scope requires existential elimination")
        if rule in {"universal_generalization", "induction_generalization"} and mode != "arbitrary":
            raise Invalid(f"GENERALIZATION {e['id']}: only arbitrary introductions may be generalized")
        if rule not in {"universal_generalization", "induction_generalization"} and generalizes:
            raise Invalid(f"GENERALIZATION {e['id']}: this closing rule cannot generalize symbols")
        if rule in {"negation_introduction", "reductio", "conditional_proof", "induction_generalization"} and not hypotheses:
            raise Invalid(f"DISCHARGES {e['id']}: this rule requires a local hypothesis")
        if rule in {"negation_introduction", "reductio"} and nodes[e["source"]]["type"] != "CONTRADICTION":
            raise Invalid(f"DISCHARGES {e['id']}: contradiction source required")
        if rule == "conditional_proof" and len(hypotheses) != 1:
            raise Invalid(f"DISCHARGES {e['id']}: conditional proof discharges one hypothesis")
        if rule == "universal_generalization" and hypotheses:
            raise Invalid(f"DISCHARGES {e['id']}: universal generalization cannot discharge a hypothesis")
        if rule == "induction_generalization" and scopes[sid]["kind"] != "induction":
            raise Invalid(f"INDUCTION {e['id']}: induction rule needs an induction scope")
        if rule == "existential_elimination" and nodes[scopes[sid]["opened_by"]].get("introduction_mode") != "witness":
            raise Invalid(f"EXISTS-ELIM {e['id']}: scope must open by taking a witness")
        if rule in {"universal_generalization", "induction_generalization"} and not e.get("generalizes"):
            raise Invalid(f"DISCHARGES {e['id']}: generalized variables are required")
        introduced = {b["id"] for b in nodes[scopes[sid]["opened_by"]].get("bindings", [])}
        if not set(generalizes).issubset(introduced):
            raise Invalid(f"DISCHARGES {e['id']}: generalized variables must belong to the closed scope opener")
        if scopes[sid]["kind"] == "induction":
            opener = scopes[sid]["opened_by"]
            first = edges[scopes[sid]["opening_edge"]]["target"]
            if nodes[opener]["type"] != "LOCAL_INTRODUCTION" or nodes[opener].get("introduction_mode") != "arbitrary" or nodes[first]["type"] != "HYPOTHESIS_LOCAL" or rule != "induction_generalization":
                raise Invalid(f"INDUCTION {sid}: arbitrary data must be followed by a local hypothesis and induction discharge")
        for hid in hypotheses:
            if hid not in nodes or nodes[hid]["type"] != "HYPOTHESIS_LOCAL" or not contains(sid, nodes[hid].get("scope")) or not reaches(hid, e["source"]):
                raise Invalid(f"DISCHARGES {e['id']}: hypothesis {hid} is not an ancestor inside the scope")

    bindings = {}
    for n in model["nodes"]:
        if n.get("strict", True) and n["type"] != "INTUITION" and "uses_symbols" not in n:
            raise Invalid(f"SYMBOL-USE {n['id']}: strict node must declare local symbol uses")
        if n["type"] in {"CONSTRUCTION", "EXISTENCE_WITNESS"} and not n.get("bindings"):
            raise Invalid(f"BINDING {n['id']}: construction or witness must bind an object")
        if n["type"] in {"CONSTRUCTION", "EXISTENCE_WITNESS"}:
            for b in n["bindings"]:
                if not all(b.get(k) for k in ("definition_latex", "well_defined", "domain_check")):
                    raise Invalid(f"BINDING {n['id']}: construction needs definition and verification")
        if n["type"] == "LOCAL_INTRODUCTION" and not n.get("introduction_mode"):
            raise Invalid(f"BINDING {n['id']}: introduction mode required")
        for b in n.get("bindings", []):
            if b["id"] in bindings:
                raise Invalid(f"BINDING {b['id']}: duplicate symbol ID")
            bound_scope = next((s["id"] for s in scopes.values() if s["opened_by"] == n["id"]), n.get("scope"))
            bindings[b["id"]] = (n, b, bound_scope)

    def visible(symbol, node_id, producer=False):
        if symbol not in bindings:
            raise Invalid(f"SYMBOL-USE {node_id}: unknown binding {symbol}")
        owner, _, bound_scope = bindings[symbol]
        node = nodes[node_id]
        if owner["id"] == node_id:
            return True
        if producer and len(outgoing[node_id]) == 1 and owner["id"] == outgoing[node_id][0] and node["type"] in {"TRANSFORM", "COMBINE"}:
            return True
        if not contains(bound_scope, node.get("scope")):
            return False
        if reaches(owner["id"], node_id):
            return True
        if owner["type"] != "LOCAL_INTRODUCTION" or not bound_scope or scopes[bound_scope]["opened_by"] != owner["id"]:
            return False
        return any(
            child.get("parent_scope") and contains(bound_scope, child["parent_scope"])
            and nodes[child["opened_by"]]["type"] == "HYPOTHESIS_LOCAL"
            and not incoming[child["opened_by"]] and not child.get("opening_edge")
            and reaches(child["opened_by"], node_id)
            for child in scopes.values()
        )

    for bid, (owner, binding, bound_scope) in bindings.items():
        for other_id, (other_node, other_binding, other_scope) in bindings.items():
            if bid != other_id and binding["symbol_latex"] == other_binding["symbol_latex"] and (contains(bound_scope, other_scope) or contains(other_scope, bound_scope) or bound_scope == other_scope):
                raise Invalid(f"BINDING-FRESH {bid}: spelling collides with visible {other_id}")
        for dep in binding["depends_on"]:
            if dep not in bindings or dep == bid or not visible(dep, owner["id"]):
                raise Invalid(f"BINDING-DEPENDENCY {bid}: dependency {dep} is unavailable")
            if owner["type"] in {"CONSTRUCTION", "EXISTENCE_WITNESS"} and dep not in owner.get("uses_symbols", []):
                raise Invalid(f"BINDING-DEPENDENCY {bid}: dependency {dep} must appear in uses_symbols")

    reserved = set()
    for row in model["symbols"]:
        bid = row.get("binding_ref")
        if bid:
            if bid not in bindings or row["symbol_latex"] != bindings[bid][1]["symbol_latex"]:
                raise Invalid(f"GLOBAL-SYMBOL {bid}: binding reference and spelling disagree")
        else:
            reserved.add(row["symbol_latex"])
    for bid, (_, binding, _) in bindings.items():
        if binding["symbol_latex"] in reserved:
            raise Invalid(f"BINDING-FRESH {bid}: spelling is reserved by the global symbol table")

    for n in model["nodes"]:
        for bid in n.get("uses_symbols", []):
            if not visible(bid, n["id"], producer=True):
                raise Invalid(f"SYMBOL-LEAK {n['id']}: {bid} is not visible")
    for e in model["edges"]:
        if e["detail_mode"] == "EDGE_DETAIL" and "uses_symbols" not in e:
            raise Invalid(f"SYMBOL-USE {e['id']}: explanatory edge must declare local symbol uses")
        for bid in e.get("uses_symbols", []):
            if not visible(bid, e["source"], producer=True):
                raise Invalid(f"SYMBOL-LEAK {e['id']}: {bid} is not visible at edge source")
        for bid in e.get("generalizes", []) + e.get("introduces_exists", []):
            if bid not in bindings or not visible(bid, e["source"], producer=True):
                raise Invalid(f"QUANTIFIER {e['id']}: {bid} is not available for binding")
        if e.get("introduces_exists") and (e["detail_mode"] != "EDGE_DETAIL" or e["relation"] == "DISCHARGES"):
            raise Invalid(f"EXISTS-INTRO {e['id']}: existential introduction needs an explanatory non-discharge edge")
    def check_formula_rows(value, owner):
        if isinstance(value, dict):
            if value.get("kind") == "formula":
                for row in value.get("symbols", []):
                    bid = row.get("binding_ref")
                    location = owner if owner in nodes else edges[owner]["source"]
                    if not bid and any(b[1]["symbol_latex"] == row["symbol_latex"] and visible(symbol, location, producer=True)
                                       for symbol, b in bindings.items()):
                        warning = f"SYMBOL-REFERENCE-RISK {owner}/{row['symbol_latex']}: local binding spelling lacks binding_ref"
                        if warning not in warnings:
                            warnings.append(warning)
                    if bid and (bid not in bindings or row["symbol_latex"] != bindings[bid][1]["symbol_latex"]):
                        raise Invalid(f"SYMBOL-TABLE {owner}: binding reference and spelling disagree")
                    if bid and bid not in (nodes[owner] if owner in nodes else edges[owner]).get("uses_symbols", []):
                        raise Invalid(f"SYMBOL-TABLE {owner}: declared formula use is missing from uses_symbols")
            for child in value.values():
                check_formula_rows(child, owner)
        elif isinstance(value, list):
            for child in value:
                check_formula_rows(child, owner)

    for n in model["nodes"]:
        check_formula_rows(n, n["id"])
    for e in model["edges"]:
        check_formula_rows(e, e["id"])

    cases = [n for n in model["nodes"] if n["type"] == "CASE"]
    for case in cases:
        cid = case["id"]
        outgoing_edges = [e for e in model["edges"] if e["source"] == cid]
        incoming_edges = [e for e in model["edges"] if e["target"] == cid]
        branches = case.get("case_branches", [])
        if len(incoming_edges) != 1 or incoming_edges[0]["relation"] != "FEEDS_CASE" or incoming_edges[0]["detail_mode"] != "STRUCTURAL_ONLY":
            raise Invalid(f"CASE {cid}: requires one structural FEEDS_CASE input")
        if not all(case.get(k) for k in ("case_input_review", "split_reason", "exhaustiveness")):
            raise Invalid(f"CASE {cid}: reading and exhaustiveness records are required")
        if case["case_mode"] == "finite" and len(branches) < 2 or case["case_mode"] == "indexed" and len(branches) != 1:
            raise Invalid(f"CASE {cid}: branch count does not match its mode")
        if {b["edge_id"] for b in branches} != {e["id"] for e in outgoing_edges}:
            raise Invalid(f"CASE {cid}: branch list differs from outgoing edges")
        paired = [n for n in model["nodes"] if n.get("paired_case") == cid]
        if len(paired) != 1 or paired[0]["type"] != "COMBINE" or paired[0].get("combine_reason") != "case_reconciliation":
            raise Invalid(f"CASE {cid}: requires one paired case-reconciliation COMBINE")
        combine = paired[0]
        if combine.get("scope") != case.get("scope"):
            raise Invalid(f"CASE {cid}: pair must close in the same local scope")
        closures = combine.get("case_closures", [])
        if len(closures) != len(branches) or {row["branch_edge"] for row in closures} != {b["edge_id"] for b in branches}:
            raise Invalid(f"CASE {cid}: paired COMBINE must close every branch exactly once")
        for row in closures:
            if row["rule"] != "case_reconciliation":
                raise Invalid(f"CASE {cid}: branch closure must use case reconciliation")
            if case["case_mode"] == "finite" and (row["generalizes"] or row["discharges"] != [row["branch_edge"]]):
                raise Invalid(f"CASE {cid}: finite branch must discharge its case condition")
            if case["case_mode"] == "indexed":
                opener = edges[row["branch_edge"]]["target"]
                matching = [part for part in combine.get("scope_closures", [])
                            if part.get("rule") == "case_reconciliation"
                            and scopes.get(part["scope"], {}).get("opened_by") == opener]
                if len(matching) != 1 or row["discharges"] or row["generalizes"] != matching[0]["generalizes"]:
                    raise Invalid(f"CASE {cid}: indexed branch must generalize its arbitrary index")
        branch_sets = []
        terminal_inputs = []
        for b in branches:
            edge = edges[b["edge_id"]]
            first = nodes[edge["target"]]
            if edge["relation"] != "CASE_BRANCH" or edge["detail_mode"] != "EDGE_DETAIL" or first["type"] in {"CASE", "COMBINE", "TRANSFORM", "HYPOTHESIS_LOCAL"} or edge.get("case_condition_latex") != b["condition_latex"] or first.get("branch_condition_latex") != b["condition_latex"]:
                raise Invalid(f"CASE-BRANCH {edge['id']}: case condition or first rectangle is invalid")
            if case["case_mode"] == "indexed" and (first["type"] != "LOCAL_INTRODUCTION" or first.get("introduction_mode") != "arbitrary"):
                raise Invalid(f"CASE {cid}: indexed branch must start with arbitrary introduction")
            seen, todo, terminals = set(), [first["id"]], []
            while todo:
                current = todo.pop()
                if current == combine["id"] or current in seen:
                    continue
                if not nodes[current].get("strict", True) or nodes[current]["type"] == "INTUITION":
                    continue
                seen.add(current)
                for target in outgoing[current]:
                    if not nodes[target].get("strict", True) or nodes[target]["type"] == "INTUITION":
                        continue
                    if target == combine["id"]:
                        terminals.append(current)
                    else:
                        todo.append(target)
            if len(set(terminals)) != 1 or any(not reaches(nid, combine["id"]) for nid in seen):
                raise Invalid(f"CASE-BRANCH {edge['id']}: branch must end once at its paired COMBINE")
            branch_sets.append(seen)
            terminal_inputs.extend(set(terminals))
        if any(branch_sets[i] & branch_sets[j] for i in range(len(branch_sets)) for j in range(i + 1, len(branch_sets))):
            raise Invalid(f"CASE {cid}: sibling branches share an intermediate result")
        expected = set(terminal_inputs)
        if case["case_mode"] == "indexed":
            expected.add(incoming_edges[0]["source"])
        if set(incoming[combine["id"]]) != expected:
            raise Invalid(f"CASE {cid}: paired COMBINE inputs do not match branch conclusions and coverage")
        for sid, scope in scopes.items():
            members = scope_members(model, sid)
            if cid in members and combine["id"] in members:
                continue
            if any(members & a and members & b for i, a in enumerate(branch_sets) for b in branch_sets[i + 1:]):
                raise Invalid(f"CASE {cid}: a local scope spans sibling branches")
            if cid in members and combine["id"] not in members and scope["closed_by"] != combine["id"]:
                raise Invalid(f"CASE {cid}: scope closes inside its case pair")
        for nested in cases:
            if nested["id"] == cid:
                continue
            inner_pair = next((n["id"] for n in model["nodes"] if n.get("paired_case") == nested["id"]), None)
            if any(nested["id"] in branch and inner_pair not in branch for branch in branch_sets):
                raise Invalid(f"CASE {cid}: nested case pair crosses a branch boundary")

    for n in model["nodes"]:
        if n["type"] != "COMBINE":
            continue
        for closure in n.get("scope_closures", []):
            sid = closure["scope"]
            if sid not in scopes or scopes[sid]["closed_by"] != n["id"]:
                raise Invalid(f"SCOPE-CLOSE {n['id']}: closure references an unrelated scope")
            introduced = {b["id"] for b in nodes[scopes[sid]["opened_by"]].get("bindings", [])}
            if not set(closure["generalizes"]).issubset(introduced):
                raise Invalid(f"SCOPE-CLOSE {n['id']}: generalized variables must come from the scope opener")
            mode = nodes[scopes[sid]["opened_by"]].get("introduction_mode")
            if closure["generalizes"] and mode != "arbitrary":
                raise Invalid(f"GENERALIZATION {n['id']}: only arbitrary introductions may be generalized")
            if mode == "witness":
                raise Invalid(f"WITNESS-CLOSE {n['id']}: witness scope requires existential elimination")
        if n.get("paired_case") and not any(c["id"] == n["paired_case"] for c in cases):
            raise Invalid(f"CASE {n['id']}: paired case does not exist")
        if n.get("case_closures") and not n.get("paired_case"):
            raise Invalid(f"CASE {n['id']}: branch closures require a paired CASE")
        obligations = n.get("induction_obligations")
        if obligations:
            if not all(key in obligations for key in ("base", "step", "principle")):
                raise Invalid(f"INDUCTION {n['id']}: base, step, and principle roles are required")
            inputs = set(incoming[n["id"]])
            base = set(obligations["base"])
            steps = obligations["step"]
            if not steps or len(steps) != len(set(steps)) or base & set(steps) or obligations["principle"] in base | set(steps):
                raise Invalid(f"INDUCTION {n['id']}: obligation roles must be distinct")
            if n.get("combine_reason") != "induction" or base | set(steps) | {obligations["principle"]} != inputs:
                raise Invalid(f"INDUCTION {n['id']}: obligations must exactly cover COMBINE inputs")
            if not base and not obligations.get("vacuous_base"):
                raise Invalid(f"INDUCTION {n['id']}: empty base needs an explanation")
            for step in steps:
                if not any(e["target"] == step and e["relation"] == "DISCHARGES" and e.get("discharge_rule") == "induction_generalization" for e in model["edges"]):
                    raise Invalid(f"INDUCTION {n['id']}: each step must be a discharged induction result")
        elif n.get("combine_reason") == "induction":
            raise Invalid(f"INDUCTION {n['id']}: obligation roles are missing")
    for sid, scope in scopes.items():
        if scope["kind"] != "induction":
            continue
        closer = edges.get(scope["closed_by"])
        if not closer:
            raise Invalid(f"INDUCTION {sid}: induction scope requires a discharge edge")
        step = closer["target"]
        matches = [n for n in model["nodes"] if step in n.get("induction_obligations", {}).get("step", [])]
        if len(matches) != 1:
            raise Invalid(f"INDUCTION {sid}: discharged step must feed exactly one induction COMBINE")
    return quantifier_dependencies(model)


def quantifier_dependencies(model):
    """Structural outer-forall/inner-exists constraints; never parse TeX claims."""
    owners = {b["id"]: (n, b) for n in model["nodes"] for b in n.get("bindings", [])}
    existential = {bid for e in model["edges"] for bid in e.get("introduces_exists", [])}
    result = set()

    def arbitrary_ancestors(bid, seen=None):
        seen = set() if seen is None else seen
        if bid in seen or bid not in owners:
            return set()
        seen.add(bid)
        owner, binding = owners[bid]
        found = {bid} if owner.get("introduction_mode") == "arbitrary" else set()
        for dep in binding["depends_on"]:
            found.update(arbitrary_ancestors(dep, seen))
        return found

    for bid in existential:
        for outer in arbitrary_ancestors(bid):
            if outer != bid:
                result.add((outer, bid))
    return sorted(result)
