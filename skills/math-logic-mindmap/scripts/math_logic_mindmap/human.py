"""Human-first model validation and presentation helpers."""
from __future__ import annotations

from .common import Invalid


def _reviewed(presentation, finding):
    rows = [r for r in presentation.get("granularity_reviews", []) if r.get("finding_id") == finding]
    return len(rows) == 1 and rows[0].get("decision") == "retain" and bool(rows[0].get("reason", "").strip())


def granularity_report(model):
    p = model["presentation"]
    incoming = {n["id"]: [] for n in model["nodes"]}
    outgoing = {n["id"]: [] for n in model["nodes"]}
    by_id = {n["id"]: n for n in model["nodes"]}
    for e in model["edges"]:
        incoming[e["target"]].append(e["source"])
        outgoing[e["source"]].append(e["target"])
    strict = {nid for nid, n in by_id.items() if n.get("strict", True) and n["type"] != "INTUITION"}
    flow_in = {nid: [] for nid in by_id}
    flow_out = {nid: [] for nid in by_id}
    for e in model["edges"]:
        if e["display_mode"] == "FLOW" and e["source"] in strict and e["target"] in strict:
            flow_in[e["target"]].append(e)
            flow_out[e["source"]].append(e)
    findings = []
    operations = [n for n in model["nodes"] if n["type"] in ("COMBINE", "TRANSFORM", "CASE")]
    semantic = [n for n in model["nodes"] if n["type"] not in ("COMBINE", "TRANSFORM", "CASE")]
    if len(p["spine"]) > 16:
        findings.append({"id": "budget-spine", "nodes": p["spine"], "reason": "The spine containing operation nodes exceeds 16 nodes"})
    if len(model["nodes"]) > 28:
        findings.append({"id": "budget-visible", "nodes": [n["id"] for n in model["nodes"]], "reason": "Visible nodes exceed 28"})
    if len(semantic) > 20:
        findings.append({"id": "budget-semantic", "nodes": [n["id"] for n in semantic], "reason": "Non-operation semantic nodes exceed 20"})
    if model["nodes"] and len(operations) / len(model["nodes"]) > .4:
        findings.append({"id": "operation-ratio", "nodes": [n["id"] for n in operations], "reason": "Operation nodes exceed 40 percent"})
    for n in model["nodes"]:
        nid = n["id"]
        if n.get("formula_latex") and len(outgoing[nid]) == 1 and n["type"] not in ("COMBINE", "TRANSFORM"):
            child = by_id[outgoing[nid][0]]
            if child.get("formula_latex") == n["formula_latex"]:
                findings.append({"id": "duplicate-" + nid, "nodes": [nid, child["id"]], "reason": "Adjacent core formulas are identical"})
        if n["type"] in ("COMBINE", "TRANSFORM") and len(outgoing[nid]) == 1:
            child = by_id[outgoing[nid][0]]
            if len(outgoing.get(child["id"], [])) == 1 and by_id[outgoing[child["id"]][0]]["type"] in ("COMBINE", "TRANSFORM"):
                findings.append({"id": "operation-result-operation-" + nid,
                                 "nodes": [nid, child["id"], outgoing[child["id"]][0]],
                                 "reason": "An operation-result-operation chain must justify the intermediate result's independent mathematical role"})
    advisories = []
    for n in model["nodes"]:
        nid = n["id"]
        if n["type"] not in ("DERIVATION", "LEMMA", "BOUND") or n.get("bindings"):
            continue
        if len(flow_in[nid]) != 1 or len(flow_out[nid]) != 1:
            continue
        before, after = flow_in[nid][0], flow_out[nid][0]
        if before["relation"] in ("COMBINE_PRODUCES", "TRANSFORM_PRODUCES", "CASE_BRANCH", "OPENS_SCOPE", "DISCHARGES"):
            continue
        if after["relation"] in ("CASE_BRANCH", "OPENS_SCOPE", "DISCHARGES"):
            continue
        finding_id = "merge-candidate-" + nid
        advisories.append({"id": finding_id, "nodes": [before["source"], nid, after["target"]],
                           "reason": "Review whether removing this one-input, one-output result loses a retention reason",
                           "reviewed": _reviewed(p, finding_id)})
    unresolved = [f for f in findings if not _reviewed(p, f["id"])]
    active_ids = {item["id"] for item in findings + advisories}
    stale_reviews = sorted({row["finding_id"] for row in p["granularity_reviews"]
                            if row["finding_id"] not in active_ids})
    return {"mode": "human-first", "findings": findings, "unresolved": unresolved,
            "advisories": advisories, "stale_reviews": stale_reviews,
            "counts": {"visible_nodes": len(model["nodes"]), "spine_nodes": len(p["spine"]),
                       "model_edges": len(model["edges"]), "visible_edges": len(model["edges"])}}


def granularity_warning(report):
    pending = [item["nodes"][1] for item in report["advisories"] if not item["reviewed"]]
    stale = report["stale_reviews"]
    if not pending and not stale:
        return None
    return (f"GRANULARITY-REVIEW: unreviewed merge candidates={len(pending)} "
            f"[{','.join(pending) or '-'}]; stale review IDs={len(stale)} "
            f"[{','.join(stale) or '-'}]")


def validate_human(model, nodes, incoming, outgoing):
    p = model.get("presentation")
    if not isinstance(p, dict) or p.get("mode") != "human-first":
        raise Invalid("HUMAN-FIRST: presentation.mode=human-first is required")
    required = ("spine", "branches", "support", "examples", "granularity_reviews")
    if any(not isinstance(p.get(k), list) for k in required):
        raise Invalid("PRESENTATION: spine/branches/support/examples/granularity_reviews must be arrays")
    branch_nodes = [i for b in p["branches"] for i in b.get("nodes", [])]
    classified = p["spine"] + branch_nodes + p["support"] + p["examples"]
    if len(classified) != len(set(classified)) or set(classified) != set(nodes):
        raise Invalid("PRESENTATION: every model node must belong exactly once to the spine, branches, support, or examples")
    for b in p["branches"]:
        if not all(b.get(k) for k in ("id", "title", "from", "to")) or b["from"] not in nodes or b["to"] not in nodes:
            raise Invalid("PRESENTATION-BRANCH: a branch lacks a stable ID, title, or legal convergence point")
    if any(nodes[i]["type"] != "INTUITION" for i in p["examples"]):
        raise Invalid("PRESENTATION: examples may contain only INTUITION nodes")
    if any(nodes[i]["type"] == "INTUITION" for i in set(nodes) - set(p["examples"])):
        raise Invalid("PRESENTATION: every INTUITION node must be in examples")
    strict = {i for i, n in nodes.items() if n.get("strict", True) and n["type"] != "INTUITION"}
    for e in model["edges"]:
        if e.get("display_mode") not in ("FLOW", "REFERENCE"):
            raise Invalid(f"DISPLAY-MODE {e['id']}: an edge must declare FLOW or REFERENCE")
        if e["display_mode"] == "REFERENCE" and e["detail_mode"] != "STRUCTURAL_ONLY":
            raise Invalid(f"REFERENCE {e['id']}: a non-proof supplementary reference must use STRUCTURAL_ONLY and must not generate an independent edge note")
        if e["display_mode"] == "REFERENCE" and e["source"] in strict and e["target"] in strict:
            raise Invalid(f"REFERENCE {e['id']}: a strict dependency must use visible FLOW")
    report = granularity_report(model)
    if report["unresolved"]:
        raise Invalid("GRANULARITY: unresolved granularity findings " + ",".join(f["id"] for f in report["unresolved"]))
    warning = granularity_warning(report)
    return [warning] if warning else []
