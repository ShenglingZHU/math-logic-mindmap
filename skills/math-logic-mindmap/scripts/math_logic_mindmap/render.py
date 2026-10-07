from __future__ import annotations

import math

from .chains import compile_chain, require_chains
from .common import CONTEXT, inline, notebook, table_cell, wiki
from .config import DEFAULT_CONFIG, config_hash, normalize_config
from .i18n import catalog
from .model import EDGE_COLORS, card_formula, node_color, node_color_role, units
from .readability import inline_formula, resolve, validate_readability

SYMBOL_HEADERS = catalog(DEFAULT_CONFIG)["symbol_headers"]
STATUS = catalog(DEFAULT_CONFIG)["status"]


def _words(config=None):
    settings = normalize_config(config)
    return settings, catalog(settings)


def table(rows, config=None):
    _, words = _words(config)
    result = ["| " + " | ".join(words["symbol_headers"]) + " |", "| --- | --- | --- | --- |"]
    for row in rows:
        values = [inline(row["symbol_latex"]), row["definition_role"], row["range_unit"], row["interpretation"]]
        result.append("| " + " | ".join(table_cell(value) for value in values) + " |")
    return "\n".join(result)


def blocks(items, config=None):
    result = []
    for block in items:
        if block["kind"] == "prose":
            result.append(block["text"])
        else:
            result.append("$$\n" + block["latex"] + "\n$$\n\n" + table(block["symbols"], config))
    return "\n\n".join(result)


def sections(items, config=None):
    return "\n\n".join("## " + section["heading"] + "\n\n" + blocks(section["blocks"], config)
                          for section in items)


def note_path(slug, nid):
    return f"note/{slug}/{nid}.md"


def note_link(slug, nid, label=None):
    return wiki(note_path(slug, nid)[:-3], label or nid)


def node_summary(model, nid, config=None):
    _, words = _words(config)
    nodes = {node["id"]: node for node in model["nodes"]}
    node = nodes[nid]
    formula = resolve(nodes, nid, node.get("reading_ref", "core"))
    text = words["labeled_value"].format(
        label=note_link(model["slug"], nid, nid + " · " + node["title"]),
        value=node["navigation"]["role"])
    if formula["kind"] == "prose":
        return text + "\n\n" + formula["text"]
    return text + "\n\n" + (inline(formula["latex"]) if inline_formula(formula["latex"])
                              else blocks([formula], config))


def input_table(model, combine, owner=None, config=None):
    _, words = _words(config)
    nodes = {node["id"]: node for node in model["nodes"]}
    result = [f'| {words["input_node"]} | {words["content_formula"]} | {words["current_use"]} |',
              "| --- | --- | --- |"]
    expanded = []
    for review in combine["input_review"]:
        node = nodes[review["node"]]
        formula = resolve(nodes, node["id"], review["formula_ref"])
        content = node["navigation"]["role"]
        if formula["kind"] == "prose":
            content += " " + formula["text"]
        elif inline_formula(formula["latex"]):
            content += " " + inline(formula["latex"])
        else:
            heading = words["input_formula"] + " " + combine["id"] + " " + node["id"]
            link = wiki(f'note/{model["slug"]}/{owner or combine["id"]}', words["complete_below"], heading)
            content += words["complete_reference"].format(link=link)
            expanded.append("#### " + heading + "\n\n" + blocks([formula], config))
        values = [note_link(model["slug"], node["id"], node["id"] + " · " + node["title"]), content, review["contribution"]]
        result.append("| " + " | ".join(table_cell(value) for value in values) + " |")
    return "\n".join(result) + ("\n\n" + "\n\n".join(expanded) if expanded else "")


def combine_context(model, combine, owner, config=None):
    _, words = _words(config)
    nodes = {node["id"]: node for node in model["nodes"]}
    target = next(edge["target"] for edge in model["edges"] if edge["source"] == combine["id"])
    formula = resolve(nodes, target, nodes[target].get("reading_ref", "core"))
    output = ((inline(formula["latex"]) if inline_formula(formula["latex"]) else blocks([formula], config))
              if formula["kind"] == "formula" else formula["text"])
    if formula.get("latex") != combine["combine_output_latex"]:
        output += "\n\n" + words["formal_output"] + inline(combine["combine_output_latex"])
    handoff = words["combined_to"].format(target=note_link(model["slug"], target))
    return (combine["combine_motivation"] + "\n\n" + input_table(model, combine, owner, config)
            + "\n\n" + handoff + combine["output_handoff"]["explanation"]
            + "\n\n" + output + "\n\n" + combine["output_handoff"]["downstream_use"])


def navigation(model, node, config=None):
    _, words = _words(config)
    slug = model["slug"]
    stage = next(item for item in model["proof_flow"] if item["id"] == node["navigation"]["stage"])
    incoming = [edge["source"] for edge in model["edges"] if edge["target"] == node["id"]]
    outgoing = [edge["target"] for edge in model["edges"] if edge["source"] == node["id"]]
    scope = next((item["title"] for item in model.get("scopes", []) if item["id"] == node.get("scope")), words["global_scope"])
    identity = (words["nonproof"] if node["type"] == "INTUITION" or not node.get("strict", True)
                else words["final_target"] if node["id"] == model["target_id"]
                else words["proof_start"] if not incoming else words["intermediate"])
    anchor = words["stage_anchor"].format(id=stage["id"], title=stage["title"])
    stage_link = wiki(f"note/{slug}/index", stage["title"], anchor)
    incoming_text = words["list_separator"].join(note_link(slug, item) for item in incoming) or words["no_predecessor"]
    outgoing_text = words["list_separator"].join(note_link(slug, item) for item in outgoing) or words["no_successor"]
    parts = ["## " + words["navigation"], words["nav_stage"].format(link=stage_link, summary=stage["summary"]),
             words["nav_role"].format(value=node["navigation"]["role"]),
             words["nav_motivation"].format(value=node["navigation"]["motivation"]),
             words["nav_position"].format(identity=identity, scope=scope),
             words["nav_neighbors"].format(incoming=incoming_text, outgoing=outgoing_text)]
    return "\n\n".join(parts) + "\n\n"


def relation_content(model, edge, other, config=None):
    _, words = _words(config)
    nodes = {node["id"]: node for node in model["nodes"]}
    source, target = nodes[edge["source"]], nodes[edge["target"]]
    owner = edge["target"] if other == edge["source"] else edge["source"]
    if nodes[other]["type"] == "COMBINE":
        text = words["labeled_value"].format(
            label=note_link(model["slug"], other, other + " · " + nodes[other]["title"]),
            value=nodes[other]["navigation"]["role"])
        text += "\n\n" + combine_context(model, nodes[other], owner, config)
    else:
        text = node_summary(model, other, config)
    if edge["detail_mode"] == "EDGE_DETAIL":
        detail = edge["detail"]
        text += "\n\n" + words["labeled_value"].format(label=words["input_contribution"], value=detail["source_contribution"])
        text += "\n\n" + words["labeled_value"].format(label=words["target_gain"], value=detail["target_gain"])
        text += "\n\n" + note_link(model["slug"], edge["id"], edge["id"] + " · " + edge["label_text"])
    elif target["type"] in ("COMBINE", "TRANSFORM"):
        value = next(item["contribution"] for item in target["input_review"] if item["node"] == source["id"])
        text += "\n\n" + words["labeled_value"].format(label=words["input_effect"], value=value)
    elif source["type"] in ("COMBINE", "TRANSFORM"):
        if other != source["id"]:
            text += "\n\n" + words["labeled_value"].format(label=words["result_handoff"], value=source["output_handoff"]["downstream_use"])
    else:
        value = next(item["contribution"] for item in target["input_context"] if item["edge_id"] == edge["id"])
        text += "\n\n" + words["labeled_value"].format(label=words["input_contribution"], value=value)
    return text


def operation_body(model, node, config=None):
    settings, words = _words(config)
    combine = node["type"] == "COMBINE"
    motivation_key = "combine_motivation" if combine else "transform_motivation"
    method_key = "combine_method" if combine else "transform_method"
    result_key = "combine_result" if combine else "transform_result"
    result = "## " + words["input_review"] + "\n\n" + input_table(model, node, config=config)
    result += "\n\n## " + words[motivation_key] + "\n\n" + node[motivation_key]
    result += "\n\n## " + words[method_key] + "\n\n" + node[method_key]
    result += "\n\n## " + words["detailed_derivation"] + "\n\n### " + words["continuous_chain"] + "\n\n"
    result += blocks([compile_chain(node, settings['language'])], config)
    pool = {block["id"]: block for block in node["derivation"]}
    chain = node["derivation_chain"]
    if chain.get("explanations"):
        result += "\n\n### " + words["step_notes"] + "\n\n" + blocks([pool[item] for item in chain["explanations"]], config)
    result += "\n\n## " + words[result_key] + "\n\n" + blocks([pool[chain["rows"][-1]["step_id"]]], config)
    result += "\n\n" + node["output_handoff"]["explanation"] + "\n\n" + node["output_handoff"]["downstream_use"]
    return result


def combine_body(model, node, config=None):
    return operation_body(model, node, config)


def transform_body(model, node, config=None):
    return operation_body(model, node, config)


def card(node, slug, model=None, config=None):
    _, words = _words(config)
    path = note_path(slug, node["id"])[:-3]
    if node["type"] == "COMBINE":
        return f"**{node['id']}**\n\nCOMBINE\n\n{words['merge']}\n\n{wiki(path, words['details'])}"
    if node["type"] == "CASE":
        return f"**{node['id']}**\n\nCASE\n\n{node['title']}\n\n{wiki(path, words['details'])}"
    if node["type"] == "TRANSFORM":
        return f"**{node['id']}**\n\nTRANSFORM\n\n{node['title']}\n\n{wiki(path, words['details'])}"
    text = f"| {node['id']} | {node['type']} |\n| :--- | ---: |\n\n### {node['title']}\n\n"
    shown_formula = card_formula(node)
    if shown_formula:
        text += "$$\n" + shown_formula + "\n$$\n\n"
    text += node["short_role"] + "\n\n---\n\n"
    text += " · ".join([wiki(path, words["details"]), wiki(path, words["in"], words["incoming"]), wiki(path, words["out"], words["outgoing"])])
    return text


def generate_notes(model, config=None):
    settings, words = _words(config)
    validate_readability(model)
    require_chains(model)
    slug = model["slug"]
    canvas = f"mindmap/{slug}.canvas"
    notes = {}
    nodes = {node["id"]: node for node in model["nodes"]}
    for node in model["nodes"]:
        nid = node["id"]
        body = (f"---\ncssclasses: [math-proof-note]\nproof_slug: {slug}\nproof_node: {nid}\nlang: {settings['language']}\n---\n\n"
                f"# {nid} · {node['title']}\n\n")
        body += words["labeled_value"].format(label=words["type"], value=f"`{node['type']}`") + "\n\n"
        body += wiki(canvas, words["locate_node"], nid) + " · " + wiki(canvas, words["open_map"]) + " · " + note_link(slug, "index", words["overview"]) + "\n\n"
        if node.get("scope"):
            body += words["scope_warning"].format(scope=node["scope"]) + "\n\n"
        body += navigation(model, node, settings)
        body += operation_body(model, node, settings) if node["type"] in ("COMBINE", "TRANSFORM") else sections(node["sections"], settings)
        if node.get("branch_condition_latex"):
            body += "\n\n## " + words["case_condition"] + "\n\n$" + node["branch_condition_latex"] + "$"
        if node["type"] == "CASE":
            body += "\n\n## " + words["case_analysis"] + "\n\n"
            source = next(e["source"] for e in model["edges"] if e["target"] == nid)
            body += note_link(slug, source) + " · " + node["case_input_review"] + "\n\n" + node["split_reason"] + "\n\n" + node["exhaustiveness"]
            if node.get("mutual_exclusivity"):
                body += "\n\n" + node["mutual_exclusivity"]
            for branch in node["case_branches"]:
                body += "\n\n- " + note_link(slug, branch["edge_id"]) + ": $" + branch["condition_latex"] + "$ → $" + branch["goal_latex"] + "$"
        if node.get("case_closures"):
            body += "\n\n## " + words["case_analysis"] + "\n\n"
            for closure in node["case_closures"]:
                body += words["case_closure_line"].format(
                    branch=note_link(slug, closure["branch_edge"]),
                    discharges=", ".join(closure["discharges"]) or "—",
                    generalizes=", ".join(closure["generalizes"]) or "—") + "\n"
        if node.get("bindings"):
            body += "\n\n## " + words["bound_symbols"] + "\n\n"
            for binding in node["bindings"]:
                body += "- " + words["labeled_value"].format(
                    label="$" + binding["symbol_latex"] + "$",
                    value="$" + binding["domain_latex"] + "$")
                if binding.get("definition_latex"):
                    body += words["clause_separator"] + "$" + binding["definition_latex"] + "$"
                body += "\n"
        if node.get("conditions"):
            lines = [words["condition_line"].format(condition=condition, check=check) for condition, check in zip(node["conditions"], node["condition_checks"])]
            body += "\n\n## " + words["conditions"] + "\n\n" + "\n".join(lines)
        for heading, key, other in [(words["incoming"], "target", "source"), (words["outgoing"], "source", "target")]:
            body += "\n\n## " + heading + "\n\n"
            related = [edge for edge in model["edges"] if edge[key] == nid]
            if not related:
                body += words["start_basis"] if key == "target" else words["branch_end"]
            for edge in related:
                body += f"### {edge['source']} → {edge['target']}\n\n" + relation_content(model, edge, edge[other], settings) + "\n\n"
        notes[note_path(slug, nid)] = notebook(body, settings["language"])
    for edge in model["edges"]:
        if edge["detail_mode"] != "EDGE_DETAIL":
            continue
        detail = edge["detail"]
        body = (f"---\ncssclasses: [math-proof-note]\nproof_slug: {slug}\nproof_edge: {edge['id']}\nlang: {settings['language']}\n---\n\n"
                f"# {edge['id']} · {edge['label_text']}\n\n")
        body += note_link(slug, edge["source"], words["source"] + " " + edge["source"]) + " → " + note_link(slug, edge["target"], words["target"] + " " + edge["target"]) + "\n\n"
        body += "## " + words["navigation"] + "\n\n" + detail["role_in_proof"] + "\n\n"
        body += node_summary(model, edge["source"], settings) + "\n\n" + node_summary(model, edge["target"], settings) + "\n\n"
        for label, nid in [(words["source"], edge["source"]), (words["target"], edge["target"])]:
            node = nodes[nid]
            latex = node.get("formula_latex") or ""
            value = f"{nid} · {node['title']} · `{node['type']}`" + (words["clause_separator"] + inline(latex) if latex and inline_formula(latex) else "")
            body += words["labeled_value"].format(label=label, value=value) + "\n\n"
        body += words["labeled_value"].format(label=words["relation"], value=f"`{edge['relation']}`") + "\n\n" + detail["summary"]
        body += "\n\n## " + words["source_contribution_heading"] + "\n\n" + detail["source_contribution"]
        body += "\n\n## " + words["transition_steps"] + "\n\n" + "\n".join(f"{index}. {step}" for index, step in enumerate(detail["transition_steps"], 1))
        if detail.get("sections"):
            body += "\n\n" + sections(detail["sections"], settings)
        checks = "\n".join("- " + words["labeled_value"].format(label=condition, value=check)
                           for condition, check in zip(detail["conditions"], detail["condition_checks"]))
        body += "\n\n## " + words["condition_checks"] + "\n\n" + (checks or words["no_new_conditions"])
        body += "\n\n## " + words["target_new"] + "\n\n" + detail["target_gain"] + "\n\n## " + words["global_role"] + "\n\n" + detail["role_in_proof"]
        if edge.get("discharges"):
            body += "\n\n" + words["discharged"] + words["list_separator"].join(note_link(slug, item) for item in edge["discharges"])
        if edge.get("case_condition_latex"):
            body += "\n\n" + words["case_condition"] + ": $" + edge["case_condition_latex"] + "$"
        if edge.get("discharge_rule"):
            body += "\n\n" + words["discharge_rule"] + ": `" + edge["discharge_rule"] + "`"
        if edge.get("generalizes"):
            body += "\n\n" + words["generalized_symbols"] + ": " + ", ".join("`" + item + "`" for item in edge["generalizes"])
        if edge.get("introduces_exists"):
            body += "\n\n" + words["existential_symbols"] + ": " + ", ".join("`" + item + "`" for item in edge["introduces_exists"])
        body += "\n\n" + wiki(canvas, words["open_map"])
        notes[note_path(slug, edge["id"])] = notebook(body, settings["language"])
    theorem = model["theorem"]
    body = f"---\ncssclasses: [math-proof-note]\nproof_slug: {slug}\nlang: {settings['language']}\n---\n\n# {theorem['title']}\n\n"
    body += wiki(canvas, words["open_proof_map"]) + "\n\n"
    body += words["labeled_value"].format(label=words["math_status"], value=words["status"][theorem["status"]])
    body += words["clause_separator"] + words["labeled_value"].format(
        label=words["proof_standard"], value=f"`{theorem['proof_standard']}`") + words["sentence_end"] + "\n\n"
    body += words["visual_notice"].format(review=note_link(slug, "_review-checklist", words["review_record"])) + "\n\n"
    body += "## " + words["theorem_content"] + "\n\n" + inline(theorem["statement_latex"])
    body += "\n\n## " + words["assumptions"] + "\n\n" + "\n".join("- " + item for item in theorem["assumptions"])
    for key, label in [("counterexample", words["counterexample"]), ("missing_assumptions", words["missing_assumptions"]), ("open_obligations", words["open_obligations"])]:
        if theorem.get(key):
            value = theorem[key]
            body += "\n\n## " + label + "\n\n" + ("\n".join("- " + item for item in value) if isinstance(value, list) else value)
    for key in CONTEXT:
        body += "\n\n## " + words["context"][key] + "\n\n" + model["context"][key]
    if model["symbols"]:
        body += "\n\n## " + words["global_symbols"] + "\n\n" + table(model["symbols"], settings)
    body += "\n\n## " + words["proof_flow"] + "\n\n"
    for stage in model["proof_flow"]:
        anchor = words["stage_anchor"].format(id=stage["id"], title=stage["title"])
        body += "### " + anchor + "\n\n" + stage["summary"] + "\n\n"
        body += words["list_separator"].join(note_link(slug, nid, nid + " · " + nodes[nid]["title"]) for nid in stage["nodes"]) + "\n\n"
    from .scope_semantics import quantifier_dependencies
    quantifier_order = quantifier_dependencies(model)
    if quantifier_order:
        spellings = {b["id"]: b["symbol_latex"] for n in model["nodes"] for b in n.get("bindings", [])}
        body += "## " + words["quantifier_dependencies"] + "\n\n"
        body += "\n".join("- $\\forall " + spellings[outer] + "$ ≺ $\\exists " + spellings[inner] + "$"
                          for outer, inner in quantifier_order) + "\n\n"
    body += "\n\n## " + words["node_index"] + "\n\n" + "\n".join("- " + note_link(slug, node["id"], node["id"] + " · " + node["title"]) for node in model["nodes"])
    body += "\n\n## " + words["edge_index"] + "\n\n" + "\n".join("- " + note_link(slug, edge["id"], edge["id"] + " · " + edge["label_text"]) for edge in model["edges"] if edge["detail_mode"] == "EDGE_DETAIL")
    notes[note_path(slug, "index")] = notebook(body, settings["language"])
    return notes


def layout(model, analysis, override=None, config=None):
    settings, words = _words(config)
    override = override or {}
    from .layout import geometry, refine_routes
    boxes, ranks, spine = geometry(model, analysis, settings)
    if not override:
        boxes = refine_routes(model, analysis, boxes, ranks)

    from .scope_semantics import scope_members

    def lane(node):
        return "__intuition" if node["type"] == "INTUITION" or not node.get("strict", True) else node.get("scope", "")

    lanes = [""] + [scope["id"] for scope in model.get("scopes", [])] + ["__intuition"]
    canvas_nodes, positions = [], {}
    for node in model["nodes"]:
        role = node_color_role(node)
        style = {"proofRole": node["type"], "proofResult": "true" if node.get("result", False) else "false",
                 "shape": "circle" if node["type"] in ("COMBINE", "CASE") else "rectangle",
                 "textAlign": "center" if node["type"] in ("COMBINE", "CASE", "TRANSFORM") else "left",
                 "border": "dashed" if lane(node) == "__intuition" else "solid"}
        if role:
            style["proofColorRole"] = role
            style["proofPaletteDefault"] = "true" if settings["node_colors"][role] == DEFAULT_CONFIG["node_colors"][role] else "false"
        item = {"id": node["id"], "type": "text", **boxes[node["id"]], "text": card(node, model["slug"], model, settings),
                "dynamicHeight": False, "styleAttributes": style}
        color = node_color(node, settings)
        if color:
            item["color"] = color
        saved = override.get("nodes", {}).get(node["id"], {})
        item.update({key: value for key, value in saved.items() if key in ("x", "y", "width", "height")})
        for key, value in saved.get("extra", {}).items():
            if key not in item:
                item[key] = value
        item["styleAttributes"] = {**saved.get("extra", {}).get("styleAttributes", {}), **item["styleAttributes"]}
        canvas_nodes.append(item)
        positions[node["id"]] = item
    groups = []
    for current_lane in lanes:
        if not current_lane:
            continue
        member_ids = scope_members(model, current_lane) if current_lane != "__intuition" else {node["id"] for node in model["nodes"] if lane(node) == current_lane}
        members = [positions[nid] for nid in member_ids]
        if not members:
            continue
        title = words["nonproof"] if current_lane == "__intuition" else next(scope["title"] for scope in model["scopes"] if scope["id"] == current_lane)
        group = {"id": "G" + current_lane.replace("-", "_"), "type": "group", "label": title,
                 "x": min(node["x"] for node in members) - 24, "y": min(node["y"] for node in members) - 48,
                 "width": max(node["x"] + node["width"] for node in members) - min(node["x"] for node in members) + 48,
                 "height": max(node["y"] + node["height"] for node in members) - min(node["y"] for node in members) + 72,
                 "color": "#999999" if current_lane == "__intuition" else "#88BBDD"}
        group.update({key: value for key, value in override.get("groups", {}).get(group["id"], {}).items() if key in ("x", "y", "width", "height")})
        for key, value in override.get("groups", {}).get(group["id"], {}).get("extra", {}).items():
            if key not in group:
                group[key] = value
        groups.append(group)
    edges = []
    for edge in model["edges"]:
        item = {"id": edge["id"], "fromNode": edge["source"], "toNode": edge["target"], "fromSide": "bottom", "toSide": "top",
                "fromFloating": False, "toFloating": False, "color": EDGE_COLORS[edge["detail_mode"]],
                "styleAttributes": {"path": "solid", "pathfindingMethod": "square"}}
        if edge["detail_mode"] == "EDGE_DETAIL":
            item["label"] = edge["label_text"]
        edges.append(item)
    theorem = model["theorem"]
    header = "# " + theorem["title"] + "\n\n**" + words["assumptions"] + "**\n\n" + "\n".join("- " + item for item in theorem["assumptions"])
    header += "\n\n**" + words["content_definitions"] + "**\n\n$$\n" + theorem["statement_latex"] + "\n$$\n\n"
    header += note_link(model["slug"], "index", words["overview_background"]) + " · " + words["status"][theorem["status"]]
    header_h = max(320, math.ceil(units(header) / 55) * 26 + 180)
    target = positions[model["target_id"]]
    head = {"id": "UIHeader", "type": "text", "x": round(target["x"] + target["width"] / 2 - 500),
            "y": min(node["y"] for node in canvas_nodes) - header_h - 104, "width": 1000, "height": header_h, "text": header}
    saved_head = override.get("nodes", {}).get("UIHeader", {})
    head.update({key: value for key, value in saved_head.items() if key in ("x", "y", "width", "height")})
    for key, value in saved_head.get("extra", {}).items():
        if key not in head:
            head[key] = value
    canvas = {"metadata": {"version": "1.0-1.0",
                           "frontmatter": {"proof_slug": model["slug"], "proof_standard": theorem["proof_standard"], "mathematical_status": theorem["status"]},
                           "proofPresentation": {"language": settings["language"], "nodeColors": settings["node_colors"], "configHash": config_hash(settings)}},
              "nodes": groups + [head] + canvas_nodes, "edges": edges}
    from .routing import prepare
    return prepare(canvas)
