from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .common import (Invalid, PERSONAL_END, digest, file_hash, managed_hash,
                     personal, personal_delimiter, read_json, safe, slug_value, write_json, write_text)
from .config import (DEFAULT_CONFIG, config_hash, load_config, model_language,
                     normalize_config, override_language)
from .i18n import catalog, visual_checks
from .model import EDGE_COLORS, estimate, model_identity, node_color, node_color_role, validate
from .render import card, generate_notes, layout, note_path
from . import __version__
from .readability import validate_readability
from .chains import require_chains
from .human import granularity_report

VISUAL_CHECKS = visual_checks(DEFAULT_CONFIG)

PROOF_PATH_MESSAGE = "PROOF-PATH: formal Proof files must be under proof/<slug>/"

PROOF_KINDS = ("proof", "layout", "manifest", "math-review", "visual-review")


def proof_relative(slug, kind):
    """Return the sole supported path for a formal proof-side JSON file."""
    slug = slug_value(slug)
    if kind not in PROOF_KINDS:
        raise Invalid(f"PROOF-PATH: unknown Proof file type {kind}")
    return f"proof/{slug}/{slug}.{kind}.json"


def proof_path(root, slug, kind, required=False):
    """Resolve a formal Proof file inside its topic directory."""
    root = Path(root).resolve()
    slug = slug_value(slug)
    current = safe(root, proof_relative(slug, kind))
    if required and not current.is_file():
        raise Invalid(f"PROOF-FILE: missing {proof_relative(slug, kind)}")
    return current


def _is_reparse_point(path):
    """Return whether a top-level deletion target redirects elsewhere."""
    path = Path(path)
    if path.is_symlink():
        return True
    try:
        attributes = os.lstat(path).st_file_attributes
    except (AttributeError, FileNotFoundError):
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _topic_targets(root, slug):
    """List exact active-topic targets in safe deletion order."""
    root = Path(root).resolve()
    slug = slug_value(slug)
    relatives = []
    work = safe(root, ".build/work")
    work_name = re.compile(rf"^{re.escape(slug)}-[0-9a-f]{{12}}$")
    if work.is_dir():
        relatives.extend(
            f".build/work/{child.name}"
            for child in sorted(work.iterdir(), key=lambda item: item.name)
            if work_name.fullmatch(child.name) and (child.is_dir() or child.is_symlink())
        )
    relatives.extend([
        f".build/staging/{slug}",
        f"mindmap/{slug}.canvas.math-logic-mindmap-tmp",
        f"mindmap/{slug}.canvas",
        f"note/{slug}",
        f".build/backups/{slug}",
    ])
    relatives.append(f"proof/{slug}")
    targets = []
    for relative in relatives:
        lexical = root.joinpath(*relative.split("/"))
        reparse = lexical.exists() and _is_reparse_point(lexical)
        path = lexical if reparse else safe(root, relative)
        exists = lexical.exists() or lexical.is_symlink()
        kind = "directory" if exists and lexical.is_dir() else "file" if exists else "missing"
        targets.append({"path": relative, "kind": kind, "exists": exists,
                        "reparse_point": reparse, "_path": path})
    return targets


def _topic_warnings(root, slug, targets):
    root = Path(root).resolve()
    proof_root = root / "proof" / slug
    proof_reparse = proof_root.exists() and _is_reparse_point(proof_root)
    manifest_path = root / proof_relative(slug, "manifest")
    manifest = None
    manifest_problem = None
    if not proof_reparse and manifest_path.is_file():
        try:
            manifest = read_json(manifest_path)
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            manifest_problem = str(exc)
    else:
        manifest_problem = "the manifest does not exist, so release ownership of notes cannot be determined"

    note_root = root / "note" / slug
    note_reparse = note_root.exists() and _is_reparse_point(note_root)
    note_entries = (sorted((p for p in note_root.rglob("*") if p.is_file() or p.is_symlink()),
                           key=lambda p: p.as_posix())
                    if note_root.is_dir() and not note_reparse else [])
    note_files = [path for path in note_entries if path.suffix == ".md" and not path.is_symlink()]
    managed = set(manifest.get("artifacts", {})) if isinstance(manifest, dict) else set()
    managed.add(f"note/{slug}/_review-checklist.md")
    personal_notes = []
    note_parse_errors = []
    for path in note_files:
        relative = path.relative_to(root).as_posix()
        if path.name == "_review-checklist.md":
            continue
        try:
            _, extra = personal(path.read_text(encoding="utf-8"))
            if extra.strip():
                personal_notes.append(relative)
        except (Invalid, OSError, UnicodeError) as exc:
            note_parse_errors.append({"path": relative, "error": str(exc)})
    unmanaged_notes = [path.relative_to(root).as_posix() for path in note_entries
                       if path.relative_to(root).as_posix() not in managed]

    modified_managed = []
    managed_file_check_errors = []
    managed_hashes = manifest.get("managed_hashes") if isinstance(manifest, dict) else None
    if manifest is not None and not isinstance(managed_hashes, dict):
        managed_file_check_errors.append({
            "path": proof_relative(slug, "manifest"),
            "error": "manifest.managed_hashes is missing or is not an object",
        })
    for relative, expected in sorted(managed_hashes.items()) if isinstance(managed_hashes, dict) else ():
        parts = PurePosixPath(relative).parts if isinstance(relative, str) else ()
        allowed = (relative == f"mindmap/{slug}.canvas" or
                   (len(parts) >= 3 and parts[:2] == ("note", slug)))
        if not allowed or any(part in ("", ".", "..") for part in parts) or "\\" in relative or ":" in relative:
            managed_file_check_errors.append({"path": str(relative),
                                              "error": "a manifest-managed path does not belong to the current topic"})
            continue
        try:
            current = safe(root, relative)
            if not current.is_file():
                continue
            changed = managed_hash(current) != expected
            if changed and relative == f"mindmap/{slug}.canvas":
                changed = persisted_canvas_hash(read_json(current)) != manifest.get("canvas_persisted_hash")
            if changed:
                modified_managed.append(relative)
        except (Invalid, OSError, UnicodeError, ValueError, TypeError) as exc:
            managed_file_check_errors.append({"path": relative, "error": str(exc)})

    standard_names = {f"{slug}.{kind}.json" for kind in PROOF_KINDS}
    standard_names |= {name + ".math-logic-mindmap-tmp" for name in standard_names}
    unexpected_proof_files = []
    if proof_root.is_dir() and not proof_reparse:
        unexpected_proof_files = [p.relative_to(root).as_posix() for p in sorted(proof_root.iterdir())
                                  if p.name not in standard_names]
    review_files = [p for p in (proof_relative(slug, "math-review"),
                                proof_relative(slug, "visual-review"))
                    if (root / Path(p)).is_file()]
    retained = _retained_backup(root, slug)
    return {
        "personal_notes": personal_notes,
        "unmanaged_note_files": unmanaged_notes,
        "note_parse_errors": note_parse_errors,
        "modified_managed_files": modified_managed,
        "managed_file_check_errors": managed_file_check_errors,
        "review_files": review_files,
        "unexpected_proof_files": unexpected_proof_files,
        "manifest_problem": manifest_problem,
        "retained_backup": _relative(root, retained),
        "unsafe_targets": [t["path"] for t in targets if t["reparse_point"]],
        "external_previews_excluded": True,
        "close_in_obsidian": True,
    }


def remove_topic(root, slug, confirm=None):
    """Preview or remove one active topic while preserving unrelated project files."""
    root = Path(root).resolve()
    slug = slug_value(slug)
    targets = _topic_targets(root, slug)
    public_targets = [{k: target[k] for k in ("path", "kind", "exists", "reparse_point")}
                      for target in targets]
    warnings = _topic_warnings(root, slug, targets)
    if confirm is None:
        return {"status": "PASS", "action": "remove-topic", "mode": "preview", "slug": slug,
                "targets": public_targets, "warnings": warnings,
                "confirmation": f"--confirm {slug}"}
    if confirm != slug:
        raise Invalid("REMOVE-CONFIRM: --confirm must exactly match the slug")
    if warnings["unsafe_targets"]:
        raise Invalid("REMOVE-REPARSE: a top-level target is a symbolic link or junction; deletion will not run: "
                      + ", ".join(warnings["unsafe_targets"]))

    removed = []
    missing = []
    for index, target in enumerate(targets):
        relative, path = target["path"], target["_path"]
        if not target["exists"]:
            missing.append(relative)
            continue
        try:
            if target["kind"] == "directory":
                shutil.rmtree(path)
            else:
                path.unlink()
            removed.append(relative)
        except OSError as exc:
            remaining = [item["path"] for item in targets[index:] if item["exists"]]
            return {"status": "FAIL", "action": "remove-topic", "mode": "confirmed",
                    "slug": slug, "removed": removed, "missing": missing,
                    "remaining": remaining, "failed_path": relative, "error": str(exc),
                    "hint": "Close the relevant tabs in Obsidian, preview again, and retry."}
    return {"status": "PASS", "action": "remove-topic", "mode": "confirmed", "slug": slug,
            "removed": removed, "missing": missing}


def require_proof_source(root, slug, source):
    """Require a manifest/build source to name the canonical model path."""
    if source != proof_relative(slug, "proof"):
        raise Invalid(PROOF_PATH_MESSAGE)
    return proof_path(root, slug, "proof", required=True)


def current_manifest(root, slug):
    """Read a topic manifest and verify its formal source path."""
    manifest = read_json(proof_path(root, slug, "manifest", required=True))
    require_proof_source(root, slug, manifest.get("source"))
    return manifest


def manifest_config(manifest):
    settings = normalize_config(manifest.get("render_config"))
    expected = manifest.get("render_config_hash")
    if expected is not None and expected != config_hash(settings):
        raise Invalid("CONFIG-SNAPSHOT: the manifest configuration snapshot is inconsistent")
    return settings


def bundle_config(root, slug):
    """Resolve a frozen build/release configuration without consulting current user settings."""
    root = Path(root).resolve()
    snapshot = root / "render-config.json"
    if snapshot.is_file():
        return normalize_config(read_json(snapshot))
    manifest_path = root / proof_relative(slug, "manifest")
    if manifest_path.is_file():
        return manifest_config(read_json(manifest_path))
    canvas_path = root / f"mindmap/{slug}.canvas"
    if canvas_path.is_file():
        presentation = read_json(canvas_path).get("metadata", {}).get("proofPresentation")
        if isinstance(presentation, dict):
            return normalize_config({"language": presentation.get("language"),
                                     "node_colors": presentation.get("nodeColors")})
    return normalize_config()


def artifact_paths(root, slug):
    root = Path(root)
    paths = [f"mindmap/{slug}.canvas"]
    folder = safe(root, f"note/{slug}")
    if folder.exists():
        paths += [p.relative_to(root).as_posix() for p in sorted(folder.glob("*.md")) if p.name != "_review-checklist.md"]
    return paths


def hashes(root, paths):
    return {p: file_hash(safe(root, p)) for p in sorted(paths)}


def presentation_identity(root):
    engine_root = Path(__file__).parent
    paths = [p for p in engine_root.rglob("*.py") if "__pycache__" not in p.parts]
    paths += list((engine_root / "schemas").glob("*.json"))
    paths += [safe(root, ".obsidian/snippets/math-logic-mindmap.css"),
              safe(root, ".obsidian/plugins/proof-routing/manifest.json"),
              safe(root, ".obsidian/plugins/proof-routing/main.js"),
              safe(root, ".obsidian/plugins/proof-routing/geometry-core.cjs")]
    files = {}
    for path in sorted(paths, key=lambda item: item.relative_to(root).as_posix() if item.is_relative_to(root) else item.as_posix()):
        relative = path.relative_to(root).as_posix() if path.is_relative_to(root) else "math_logic_mindmap/" + path.relative_to(engine_root).as_posix()
        files[relative] = file_hash(path) if path.is_file() else "not-installed"
    return {"files": files, "digest": digest({"tool": __version__, "files": files})}


def checklist(slug, state="UNREVIEWED", evidence=None, config=None):
    settings = normalize_config(config)
    words = catalog(settings)
    checks = visual_checks(settings)
    visual_state = words["labeled_value"].format(label=words["visual_state"], value=f"**{state}**")
    text = f"# {slug} · {words['review_title']}\n\n{visual_state}\n\n"
    text += words["review_intro"] + "\n\n"
    for k, v in checks.items():
        checked = evidence and evidence.get("checks", {}).get(k, {}).get("status") == "PASS"
        text += f"- [{'x' if checked else ' '}] `{k}` {v}\n"
    text += f"\n## {words['route_convention']}\n\n{words['route_text']}\n\n"
    text += f"## {words['environment_record']}\n\n{words['environment_text']}\n"
    if evidence:
        text += "\n" + words["labeled_value"].format(label=words["reviewer"], value=evidence["reviewer"])
        text += "\n\n" + words["labeled_value"].format(label=words["environment"], value="`" + json.dumps(evidence["environment"], ensure_ascii=False) + "`") + "\n"
    return text


def rect_overlap(a, b, margin=0):
    return (a["x"] < b["x"] + b["width"] + margin and a["x"] + a["width"] + margin > b["x"]
            and a["y"] < b["y"] + b["height"] + margin and a["y"] + a["height"] + margin > b["y"])


def check_canvas(model, canvas, analysis, routing_report=None, config=None):
    settings = normalize_config(config)
    from jsonschema import Draft202012Validator
    schema = read_json(Path(__file__).parent / "schemas/canvas.schema.json")
    found = list(Draft202012Validator(schema).iter_errors(canvas))
    if found:
        raise Invalid("CANVAS-SCHEMA: " + "; ".join(e.message for e in found[:6]))
    errors, warnings = [], []
    ns, es = canvas.get("nodes", []), canvas.get("edges", [])
    from .routing import MIN_RANK_GAP, ROUTING_PROFILE, active, require_clear
    if not active(canvas):
        raise Invalid(f'ROUTE-PROFILE: requires {ROUTING_PROFILE}')
    for edge in es:
        route = edge.get("proofRoute", {})
        if any(not isinstance(route.get(key), (int, float)) or not math.isfinite(route[key])
               for key in ("fromOffset", "toOffset", "midOffset")):
            raise Invalid(f"ROUTE {edge.get('id')}: a route offset must be a finite number")
    all_ids = [x.get("id") for x in ns + es]
    if len(set(all_ids)) != len(all_ids):
        errors.append("CANVAS: duplicate IDs")
    by_id = {n.get("id"): n for n in ns}
    by_edge = {e.get("id"): e for e in es}
    expected_nodes = {n["id"] for n in model["nodes"]}
    defaults = layout(model, analysis, config=settings)
    expected_display = {n["id"] for n in defaults["nodes"]}
    if set(by_id) != expected_display:
        errors.append("CANVAS: header/group/card sets are incomplete or contain unmanaged nodes")
    if canvas.get("metadata", {}).get("version") != "1.0-1.0":
        errors.append("CANVAS: Advanced JSON Canvas version is missing or unsupported")
    expected_presentation = {"language": settings["language"], "nodeColors": settings["node_colors"],
                             "configHash": config_hash(settings)}
    if canvas.get("metadata", {}).get("proofPresentation") != expected_presentation:
        errors.append("CANVAS: proofPresentation does not match the build configuration")
    if {i for i in by_id if not str(i).startswith(("UI", "G"))} != expected_nodes:
        errors.append("CANVAS: proof-node set does not match the model")
    expected_visible_edges = {e["id"] for e in model["edges"]}
    if set(by_edge) != expected_visible_edges:
        errors.append("CANVAS: visible-edge set does not match model display_mode")
    if errors:
        raise Invalid("; ".join(errors))
    header = next(n for n in defaults["nodes"] if n["id"] == "UIHeader")
    require_clear(canvas, routing_report)
    if by_id["UIHeader"].get("text") != header["text"]:
        errors.append("HEADER: header content does not match the model")
    if by_id["UIHeader"]["width"] < header["width"] or by_id["UIHeader"]["height"] < header["height"]:
        errors.append("HEADER: header dimensions are below the estimate")
    for n in ns:
        for k in ("x", "y", "width", "height"):
            if type(n.get(k)) is not int or (k in ("width", "height") and n[k] <= 0):
                errors.append(f"CANVAS {n['id']}: invalid {k}")
    if errors:
        raise Invalid("; ".join(errors))
    cards = [n for n in ns if n["type"] != "group"]
    for i, a in enumerate(cards):
        for b in cards[i + 1:]:
            if rect_overlap(a, b):
                errors.append(f"OVERLAP {a['id']} / {b['id']}: cards overlap")
    for n in model["nodes"]:
        c = by_id[n["id"]]
        if c.get("type") != "text" or c.get("text") != card(n, model["slug"], model, settings):
            errors.append(f"CONTENT {n['id']}: card content differs from the model")
        if c.get("color") != node_color(n, settings):
            errors.append(f"COLOR {n['id']}: color mapping is inconsistent")
        role = node_color_role(n)
        style = c.get("styleAttributes", {})
        if role:
            default_flag = "true" if settings["node_colors"][role] == DEFAULT_CONFIG["node_colors"][role] else "false"
            if style.get("proofColorRole") != role or style.get("proofPaletteDefault") != default_flag:
                errors.append(f"COLOR-ROLE {n['id']}: color role or default marker is inconsistent")
        elif "proofColorRole" in style or "proofPaletteDefault" in style:
            errors.append(f"COLOR-ROLE {n['id']}: an uncolored node must not declare a color role")
        if c.get("styleAttributes", {}).get("proofRole") != n["type"]:
            errors.append(f"TYPE {n['id']}: style type does not match the model")
        if c.get("styleAttributes", {}).get("proofResult") != ("true" if n.get("result", False) else "false"):
            errors.append(f"RESULT-STYLE {n['id']}: result styling does not match the model")
        size = estimate(n, settings)
        if c["width"] < size["width"] or c["height"] < size["height"]:
            errors.append(f"SIZE {n['id']}: below the estimated content minimum {size['width']}×{size['height']}")
        if n["type"] in ("COMBINE", "CASE") and (c["width"] != c["height"] or c.get("styleAttributes", {}).get("shape") != "circle"):
            errors.append(f"{n['type']} {n['id']}: requires a circle with equal width and height")
        if n["type"] == "TRANSFORM" and (c["width"] < 240 or c["height"] < 180 or c.get("styleAttributes", {}).get("shape") != "rectangle"):
            errors.append(f"TRANSFORM {n['id']}: requires a rectangular interaction container of at least 240×180")
    for e in model["edges"]:
        c = by_edge[e["id"]]
        s, t = by_id[e["source"]], by_id[e["target"]]
        if c.get("fromNode") != s["id"] or c.get("toNode") != t["id"]:
            errors.append(f"ENDPOINT {e['id']}: source or target is inconsistent")
        if t["y"] - s["y"] - s["height"] < MIN_RANK_GAP:
            errors.append(f"RANK {e['id']}: must point downward with at least {MIN_RANK_GAP}px between rectangles")
        for k in ("fromSide", "toSide"):
            if c.get(k) not in ("top", "bottom", "left", "right"):
                errors.append(f"SIDE {e['id']}: illegal connection side")
        if c.get("fromEnd", "none") != "none" or c.get("toEnd", "arrow") != "arrow":
            errors.append(f"ARROW {e['id']}: must be a one-way arrow")
        if c.get("fromFloating") or c.get("toFloating"):
            errors.append(f"FLOATING {e['id']}: floating connections are prohibited by default")
        if c.get("styleAttributes", {}).get("pathfindingMethod") != "square":
            errors.append(f"ROUTE {e['id']}: native fallback must use square")
        if c.get("color") != EDGE_COLORS[e["detail_mode"]]:
            errors.append(f"EDGE-COLOR {e['id']}: color is inconsistent")
        if c.get("label") != (e["label_text"] if e["detail_mode"] == "EDGE_DETAIL" else None):
            errors.append(f"LABEL {e['id']}: label does not match the explanation mode")
        gap = t["y"] - s["y"] - s["height"]
        if gap > 400:
            warnings.append(f"COMPACTION {e['id']}: vertical clearance {gap}px; inspect long-range reuse and grouping needs")
    from .diagnostics import port_collisions
    warnings.extend(f"PORT-COLLISION {item['node']} {item['side']} {item['offset']}: {', '.join(item['edges'])}"
                    for item in port_collisions(canvas))
    # Groups are containers, but must not enclose unrelated proof cards.
    from .scope_semantics import scope_members
    scopes = {"G" + s["id"].replace("-", "_"): s["id"] for s in model.get("scopes", [])}
    scopes["G__intuition"] = "__intuition"
    for g in [n for n in ns if n["type"] == "group"]:
        scope = scopes.get(g["id"])
        if scope is None:
            errors.append(f"GROUP {g['id']}: unmodeled group")
            continue
        for n in model["nodes"]:
            c = by_id[n["id"]]
            member = (n["type"] == "INTUITION" or not n.get("strict", True)) if scope == "__intuition" else n["id"] in scope_members(model, scope)
            inside = g["x"] <= c["x"] and g["y"] <= c["y"] and g["x"] + g["width"] >= c["x"] + c["width"] and g["y"] + g["height"] >= c["y"] + c["height"]
            if member and not inside:
                errors.append(f"GROUP {g['id']}: does not contain member {n['id']}")
            if not member and rect_overlap(g, c):
                errors.append(f"GROUP {g['id']}: intersects non-member {n['id']}")
    if errors:
        raise Invalid("; ".join(errors))
    return warnings


def validate_bundle(root, model, config=None):
    from .routing import analyze
    root = Path(root).resolve()
    settings = normalize_config(config) if config is not None else bundle_config(root, model["slug"])
    info = validate(model)
    validate_readability(model)
    require_chains(model)
    slug = model["slug"]
    canvas = read_json(safe(root, f"mindmap/{slug}.canvas"))
    routing_report = analyze(canvas)
    warnings = check_canvas(model, canvas, info, routing_report, settings)
    expected = generate_notes(model, settings)
    actual = {p.relative_to(root).as_posix() for p in safe(root, f"note/{slug}").glob("*.md") if p.name != "_review-checklist.md"}
    if actual != set(expected):
        raise Invalid("NOTES: file set does not match nodes and explanatory edges")
    for relative, text in expected.items():
        current = safe(root, relative).read_text(encoding="utf-8")
        if personal(current)[0] != personal(text)[0]:
            raise Invalid(f"NOTE-CONTENT {relative}: a generated region was edited or does not match the model")
    for e in model["edges"]:
        if e["detail_mode"] == "EDGE_DETAIL":
            needle = f"[[note/{slug}/{e['id']}|"
            words = catalog(settings)
            for nid, section in ((e["source"], words["outgoing"]), (e["target"], words["incoming"])):
                text = safe(root, note_path(slug, nid)).read_text(encoding="utf-8")
                part = text.split("## " + section + "\n", 1)[1].split("\n## ", 1)[0]
                if needle not in part:
                    raise Invalid(f"EDGE-NAV {e['id']}: {section} is unreachable from {nid}")
    # Resolve generated links, headings and plugin node fragments against this bundle root.
    texts = [personal(safe(root, p).read_text(encoding="utf-8"))[0] for p in expected]
    texts += [n["text"] for n in canvas["nodes"] if n["type"] == "text"]
    for text in texts:
        for link in re.findall(r"\[\[([^\]]+)\]\]", text):
            # Decode only Markdown's escaped alias separator, never arbitrary path backslashes.
            target = re.split(r"\\?\|", link, maxsplit=1)[0]
            path, _, fragment = target.partition("#")
            if not path:
                if fragment not in re.findall(r"^#+ (.+)$", text, re.M):
                    raise Invalid(f"LINK: heading does not exist on this page {target}")
                continue
            if not path.endswith((".canvas", ".md")):
                path += ".md"
            dest = safe(root, path)
            if not dest.is_file():
                raise Invalid(f"LINK: target does not exist {target}")
            if fragment:
                if dest.suffix == ".canvas":
                    if fragment not in {n["id"] for n in read_json(dest)["nodes"]}:
                        raise Invalid(f"LINK: node does not exist {target}")
                elif fragment not in re.findall(r"^#+ (.+)$", dest.read_text(encoding="utf-8"), re.M):
                    raise Invalid(f"LINK: heading does not exist {target}")
    return {"machine": "PASS", "visual": "UNREVIEWED", "warnings": info["warnings"] + warnings,
            "counts": {"model_nodes": len(model["nodes"]), "model_edges": len(model["edges"]),
                       "visible_nodes": len(model["nodes"]), "visible_edges": len(model["edges"]), "notes": len(expected)},
            "routing": routing_report}


def build(root, model_path, relayout=False, layout_report=False, language=None):
    root = Path(root).resolve()
    settings = override_language(load_config(root), language)
    from .routing import ROUTING_PROFILE, environment
    route_environment = environment(root)
    model_path = Path(model_path).resolve()
    if not model_path.is_relative_to(root):
        raise Invalid("The model file must be inside the project")
    model = read_json(model_path)
    info = validate(model)
    if model_language(model) != settings["language"]:
        raise Invalid(f"CONFIG-LANGUAGE: model language is {model_language(model)} and current build language is {settings['language']}; "
                      "change the model/root configuration or temporarily override it with build --language <model language>")
    validate_readability(model)
    require_chains(model)
    slug = model["slug"]
    if model_path != proof_path(root, slug, "proof"):
        raise Invalid(PROOF_PATH_MESSAGE)
    stage = safe(root, f".build/staging/{slug}")
    override_path = proof_path(root, slug, "layout")
    override = read_json(override_path) if override_path.exists() and not relayout else {}
    c = layout(model, info, override, settings)
    notes = generate_notes(model, settings)
    # First validate entirely in a new staging directory; never edit published notes here.
    temp = safe(root, f".build/work/{slug}-{digest(c)[:12]}")
    if temp.exists():
        shutil.rmtree(temp)
    write_json(temp / f"mindmap/{slug}.canvas", c)
    write_json(temp / "render-config.json", settings)
    for p, content in notes.items():
        write_text(temp / p, content)
    write_text(temp / f"note/{slug}/_review-checklist.md", checklist(slug, config=settings))
    # Persist candidate evidence before any gate can reject the build.
    from .diagnostics import summarize
    from .routing import analyze
    routing = analyze(c)
    write_json(temp / 'reports/routing.json', routing)
    write_json(temp / 'reports/diagnostics.json', summarize(c, routing))
    write_json(temp / 'reports/granularity.json', granularity_report(model))
    try:
        report = validate_bundle(temp, model, settings)
    except Invalid as exc:
        write_json(temp / 'failure.json', {'status': 'BLOCKED', 'model_hash': model_identity(model),
                   'layout_hash': digest(override), 'render_config_hash': config_hash(settings),
                   'environment': route_environment, 'reason': str(exc)})
        raise
    from .layout import VERSION, geometry, metrics, diagnostic_svg, combine_feed_details
    _, display_layers, mainline = geometry(model, info, settings)
    measured = metrics(model, c, routing)
    levels = {y: i for i, y in enumerate(sorted({n['y'] for n in c['nodes'] if n['type'] == 'text'}))}
    display_layers = {n['id']: levels[n['y']] for n in c['nodes'] if n['type'] == 'text'}
    layout_summary = {'coordinate_algorithm': VERSION, 'routing_profile': ROUTING_PROFILE,
        'display_layers': display_layers, 'mainline': mainline,
        'layout_metrics': measured, 'visual': 'UNREVIEWED',
        'size_range': {k: [min(n[k] for n in c['nodes'] if n['type']=='text'), max(n[k] for n in c['nodes'] if n['type']=='text')] for k in ('width','height')},
        'pending_visual_checks': ['labels', 'arrowheads', 'zoom readability'],
        'diagnostics_report': 'reports/diagnostics.json'}
    old_canvas = root / f'mindmap/{slug}.canvas'
    if old_canvas.exists():
        previous = read_json(old_canvas)
        from .routing import active
        if active(previous) and {n['id'] for n in previous['nodes']} == {n['id'] for n in c['nodes']}:
            layout_summary['previous_layout_metrics'] = metrics(model, previous)
    if layout_report:
        layout_summary['combine_feed_details'] = combine_feed_details(model, c, routing)
        write_text(temp / 'layout.svg', diagnostic_svg(c))
        write_json(temp / 'layout-report.json', {**layout_summary, 'routing_report': 'reports/routing.json'})
    write_json(temp / "model.json", model)
    routing_result = report.pop("routing")
    if routing_result != routing:
        raise Invalid("ROUTING-REPORT: validation results are inconsistent within one build")
    report_hashes = hashes(temp, ["reports/routing.json", "reports/diagnostics.json", "reports/granularity.json"])
    machine_summary = {"machine": report["machine"], "visual": report["visual"],
                       "warnings": report["warnings"], "counts": report["counts"],
                       "environment": route_environment}
    write_json(temp / "build.json", {"slug": slug, "source": model_path.relative_to(root).as_posix(), "model_hash": model_identity(model),
        "layout_hash": digest(override), "render_config_hash": config_hash(settings), "relayout": relayout,
        "artifacts": hashes(temp, artifact_paths(temp, slug)),
        "reports": report_hashes, "machine": machine_summary,
        "layout": {"coordinate_algorithm": VERSION, "routing_profile": ROUTING_PROFILE}})
    if stage.exists():
        shutil.rmtree(stage)
    stage.parent.mkdir(parents=True, exist_ok=True)
    work_parent = temp.parent
    temp.rename(stage)
    if work_parent.exists() and not any(work_parent.iterdir()):
        work_parent.rmdir()
    return machine_summary


def semantic_canvas(canvas):
    return {"nodes": {n["id"]: {k: n.get(k) for k in ("id", "type", "text", "label", "file", "subpath")} for n in canvas["nodes"]},
            "edges": {e["id"]: {k: e.get(k) for k in ("id", "fromNode", "toNode", "label")} for e in canvas["edges"]}}


def persisted_canvas(canvas):
    """Normalize defaults that Obsidian omits when it saves a Canvas."""
    result = copy.deepcopy(canvas)
    for edge in result["edges"]:
        if edge.get("fromEnd", "none") == "none":
            edge.pop("fromEnd", None)
        if edge.get("toEnd", "arrow") == "arrow":
            edge.pop("toEnd", None)
    result["nodes"] = sorted(result["nodes"], key=lambda item: item["id"])
    result["edges"] = sorted(result["edges"], key=lambda item: item["id"])
    return result


def persisted_canvas_hash(canvas):
    return digest(persisted_canvas(canvas))


def import_layout(root, slug):
    root = Path(root).resolve()
    slug_value(slug)
    manifest = current_manifest(root, slug)
    settings = manifest_config(manifest)
    path = safe(root, f"mindmap/{slug}.canvas")
    canvas = read_json(path)
    if semantic_canvas(canvas) != manifest["canvas_semantic"]:
        raise Invalid("ROUNDTRIP: text, node-set, or logical-edge changes detected; apply them to the Proof Model first because this command imports layout only")
    result = {"version": 1, "nodes": {}, "groups": {}, "imported_canvas_hash": file_hash(path)}
    for n in canvas["nodes"]:
        if n["type"] == "group":
            result["groups"][n["id"]] = {k: n[k] for k in ("x", "y", "width", "height")}
            result["groups"][n["id"]]["extra"] = {k: v for k, v in n.items() if k not in ("id", "type", "x", "y", "width", "height", "label", "color")}
        else:
            result["nodes"][n["id"]] = {k: n[k] for k in ("x", "y", "width", "height")}
            result["nodes"][n["id"]]["extra"] = {k: v for k, v in n.items() if k not in ("id", "type", "x", "y", "width", "height", "text", "color", "dynamicHeight")}
    model = read_json(require_proof_source(root, slug, manifest["source"]))
    check_canvas(model, layout(model, validate(model), result, settings), validate(model), config=settings)
    write_json(proof_path(root, slug, "layout"), result)
    manifest["visual"] = {"status": "STALE", "reason": "Regeneration and review are required after layout import"}
    write_json(proof_path(root, slug, "manifest"), manifest)
    write_text(safe(root, f"note/{slug}/_review-checklist.md"), checklist(slug, "STALE", config=settings))
    return {"imported": slug, "nodes": len(result["nodes"]), "visual": "STALE"}


BACKUP_STAMP = re.compile(r"^\d{8}T\d{12}Z$")


def _retain_latest_backup(root, slug, latest):
    parent = safe(root, f".build/backups/{slug}")
    for child in parent.iterdir() if parent.exists() else ():
        if child.is_dir() and child != latest and BACKUP_STAMP.fullmatch(child.name):
            shutil.rmtree(child)


def _retained_backup(root, slug):
    parent = safe(root, f".build/backups/{slug}")
    candidates = sorted(child for child in parent.iterdir()
                        if child.is_dir() and BACKUP_STAMP.fullmatch(child.name)) if parent.exists() else []
    return candidates[-1] if candidates else None


def _relative(root, path):
    return path.relative_to(root).as_posix() if path else None


def _manifest_state(manifest):
    result = copy.deepcopy(manifest)
    result.pop("released_at", None)
    return result


def _write_manifest_atomic(path, manifest):
    temp = path.with_name(path.name + ".math-logic-mindmap-tmp")
    write_json(temp, manifest)
    temp.replace(path)


def release(root, slug):
    root = Path(root).resolve()
    slug_value(slug)
    from .routing import require_release_proof_routing_sync
    require_release_proof_routing_sync(root)
    stage = safe(root, f".build/staging/{slug}")
    meta = read_json(stage / "build.json")
    model = read_json(stage / "model.json")
    settings = normalize_config(read_json(stage / "render-config.json"))
    if config_hash(settings) != meta.get("render_config_hash"):
        raise Invalid("STALE: staged build configuration changed; rebuild")
    model_path = require_proof_source(root, slug, meta.get("source"))
    if digest(read_json(model_path)) != meta["model_hash"]:
        raise Invalid("STALE: model changed; rebuild first")
    override_path = proof_path(root, slug, "layout")
    override = read_json(override_path) if override_path.exists() and not meta["relayout"] else {}
    if digest(override) != meta["layout_hash"]:
        raise Invalid("STALE: layout changed; rebuild first")
    if hashes(stage, artifact_paths(stage, slug)) != meta["artifacts"]:
        raise Invalid("STALE: staged files changed; rebuild")
    if hashes(stage, meta["reports"].keys()) != meta["reports"]:
        raise Invalid("STALE: staged report changed; rebuild")
    validation = validate_bundle(stage, model, settings)
    validation.pop("routing")
    review_warnings = [w for w in validation["warnings"] if w.startswith("GRANULARITY-REVIEW:")]
    review_notice = {"warnings": review_warnings} if review_warnings else {}
    review_path = proof_path(root, slug, "math-review")
    review = read_json(review_path) if review_path.exists() else None
    if review and review.get("model_hash") != meta["model_hash"]:
        review = {"status": "STALE", "summary": "Optional review does not match the released model."}
    manifest_path = proof_path(root, slug, "manifest")
    old = read_json(manifest_path) if manifest_path.exists() else None
    if old and old["title"] != model["theorem"]["title"]:
        raise Invalid("SLUG-CONFLICT: the same slug refers to a different entity name; choose an explicit new name")
    formal = {p: safe(stage, p).read_bytes() for p in meta["artifacts"]}
    obsolete = set(old["artifacts"]) - set(meta["artifacts"]) if old else set()
    for p in set(formal) | obsolete:
        current = safe(root, p)
        if not current.exists():
            continue
        if not old or p not in old["managed_hashes"]:
            raise Invalid(f"CONFLICT: existing unmanaged file {p}")
        imported = p.endswith(".canvas") and override_path.exists() and file_hash(current) == read_json(override_path).get("imported_canvas_hash")
        formatting_only = p.endswith('.canvas') and persisted_canvas_hash(read_json(current)) == old.get('canvas_persisted_hash')
        if managed_hash(current) != old["managed_hashes"][p] and not imported and not formatting_only:
            raise Invalid(f"CONFLICT: generated region was edited manually {p}; card layout may be imported first")
        if current.suffix == ".md":
            _, extra = personal(current.read_text(encoding="utf-8"))
            if p in obsolete and extra.strip():
                raise Invalid(f"CONFLICT: a note to be removed contains personal content; save it separately first {p}")
            if p in formal:
                formal[p] = (personal(formal[p].decode())[0] + personal_delimiter(settings["language"])
                             + extra + PERSONAL_END).encode()

    checklist_relative = f"note/{slug}/_review-checklist.md"
    checklist_path = safe(root, checklist_relative)
    formal_previous = {p: safe(root, p).read_bytes() if safe(root, p).exists() else None
                       for p in set(formal) | obsolete}
    artifacts_changed = bool(obsolete) or any(formal_previous[p] != data for p, data in formal.items())
    presentation = presentation_identity(root)
    presentation_changed = not old or old.get("presentation_hash") != presentation
    reset_visual = artifacts_changed or presentation_changed
    visual = {"status": "UNREVIEWED"} if reset_visual else copy.deepcopy(old.get("visual", {"status": "UNREVIEWED"}))
    if reset_visual or not checklist_path.exists():
        checklist_bytes = checklist(slug, config=settings).encode()
    else:
        checklist_bytes = checklist_path.read_bytes()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = safe(root, f".build/backups/{slug}/{stamp}")
    old_manifest_bytes = manifest_path.read_bytes() if manifest_path.exists() else None

    def make_manifest(final_validation, released_at):
        machine = {"machine": final_validation["machine"], "visual": final_validation["visual"],
                   "warnings": final_validation["warnings"], "counts": final_validation["counts"],
                   "reports": meta["reports"]}
        released_canvas = read_json(safe(root, f"mindmap/{slug}.canvas"))
        paths = artifact_paths(root, slug)
        manifest = {"slug": slug, "title": model["theorem"]["title"], "source": meta["source"],
            "model_hash": meta["model_hash"], "machine": machine, "mathematical_review": review,
            "visual": visual, "artifacts": hashes(root, paths),
            "render_config": settings, "render_config_hash": config_hash(settings),
            "presentation_hash": presentation,
            "managed_hashes": {p: managed_hash(safe(root, p)) for p in paths},
            "model_nodes": len(model["nodes"]), "model_edges": len(model["edges"]),
            "visible_nodes": len(model["nodes"]), "visible_edges": len(model["edges"]),
            "canvas_semantic": semantic_canvas(released_canvas),
            "canvas_persisted_hash": persisted_canvas_hash(released_canvas), "released_at": released_at}
        return manifest, machine

    if not artifacts_changed:
        final_validation = validate_bundle(root, model, settings)
        final_validation.pop("routing")
        manifest, machine = make_manifest(final_validation, stamp)
        retained = _retained_backup(root, slug)
        if old and _manifest_state(old) == _manifest_state(manifest) and checklist_path.exists() and checklist_path.read_bytes() == checklist_bytes:
            return {"released": slug, "machine": "PASS", "visual": old["visual"]["status"],
                    "change_kind": "none", "backup_created": False, "backup": None,
                    "retained_backup": _relative(root, retained), "counts": machine["counts"], **review_notice}
        checklist_previous = checklist_path.read_bytes() if checklist_path.exists() else None
        try:
            if checklist_previous != checklist_bytes:
                temp = safe(root, checklist_relative + ".math-logic-mindmap-tmp")
                temp.write_bytes(checklist_bytes)
                temp.replace(checklist_path)
            _write_manifest_atomic(manifest_path, manifest)
        except Exception as exc:
            safe(root, checklist_relative + ".math-logic-mindmap-tmp").unlink(missing_ok=True)
            manifest_path.with_name(manifest_path.name + ".math-logic-mindmap-tmp").unlink(missing_ok=True)
            if checklist_previous is None:
                checklist_path.unlink(missing_ok=True)
            else:
                checklist_path.write_bytes(checklist_previous)
            if old_manifest_bytes is None:
                manifest_path.unlink(missing_ok=True)
            else:
                manifest_path.write_bytes(old_manifest_bytes)
            restored = ((not checklist_path.exists()) if checklist_previous is None else
                        file_hash(checklist_path) == hashlib.sha256(checklist_previous).hexdigest())
            restored = restored and ((not manifest_path.exists()) if old_manifest_bytes is None else
                                     file_hash(manifest_path) == hashlib.sha256(old_manifest_bytes).hexdigest())
            if restored:
                raise
            raise Invalid(f"RECOVERY-HIGH: metadata release failed and restored hashes do not match; original error: {exc}") from exc
        return {"released": slug, "machine": "PASS", "visual": visual["status"],
                "change_kind": "metadata", "backup_created": False, "backup": None,
                "retained_backup": _relative(root, retained), "counts": machine["counts"], **review_notice}

    proposed = dict(formal)
    proposed[checklist_relative] = checklist_bytes
    changes = set(proposed) | obsolete
    previous = {p: safe(root, p).read_bytes() if safe(root, p).exists() else None for p in changes}
    has_previous = old_manifest_bytes is not None or any(data is not None for data in previous.values())
    if has_previous:
        for p, data in previous.items():
            if data is not None:
                dest = safe(backup, p); dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
        if old_manifest_bytes:
            dest = backup / "manifest.json"; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(old_manifest_bytes)
    try:
        for p, data in proposed.items():
            dest = safe(root, p); dest.parent.mkdir(parents=True, exist_ok=True)
            temp = safe(root, p + ".math-logic-mindmap-tmp"); temp.write_bytes(data); temp.replace(dest)
        for p in obsolete:
            safe(root, p).unlink()
        final_validation = validate_bundle(root, model, settings)
        final_validation.pop("routing")
        manifest, machine = make_manifest(final_validation, stamp)
        _write_manifest_atomic(manifest_path, manifest)
    except Exception as exc:
        for p in changes:
            safe(root, p + ".math-logic-mindmap-tmp").unlink(missing_ok=True)
        manifest_path.with_name(manifest_path.name + ".math-logic-mindmap-tmp").unlink(missing_ok=True)
        for p, data in previous.items():
            dest = safe(root, p)
            if data is None:
                dest.unlink(missing_ok=True)
            else:
                dest.write_bytes(data)
        if old_manifest_bytes:
            manifest_path.write_bytes(old_manifest_bytes)
        else:
            manifest_path.unlink(missing_ok=True)
        restored = all((not safe(root, p).exists()) if data is None else
                       (safe(root, p).is_file() and file_hash(safe(root, p)) == hashlib.sha256(data).hexdigest())
                       for p, data in previous.items())
        restored = restored and ((not manifest_path.exists()) if old_manifest_bytes is None else
                                  file_hash(manifest_path) == hashlib.sha256(old_manifest_bytes).hexdigest())
        if restored:
            if has_previous and backup.exists():
                shutil.rmtree(backup)
            raise
        location = backup.relative_to(root).as_posix() if has_previous else "(no backup created)"
        raise Invalid(f"RECOVERY-HIGH: release failed and restored hashes do not match; backup retained at {location}; original error: {exc}") from exc
    if has_previous:
        _retain_latest_backup(root, slug, backup)
    retained = _retained_backup(root, slug)
    return {"released": slug, "machine": "PASS", "visual": visual["status"],
            "change_kind": "artifacts", "backup_created": has_previous,
            "backup": _relative(root, backup) if has_previous else None,
            "retained_backup": _relative(root, retained), "counts": machine["counts"], **review_notice}


def artifacts_match_manifest(root, slug, manifest, current):
    if current == manifest["artifacts"]:
        return True
    if current.keys() != manifest["artifacts"].keys():
        return False
    canvas_path = f"mindmap/{slug}.canvas"
    if any(path != canvas_path for path in current if current[path] != manifest["artifacts"][path]):
        return False
    try:
        return persisted_canvas_hash(read_json(safe(root, canvas_path))) == manifest.get("canvas_persisted_hash")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        return False


def record_review(root, slug, evidence_path):
    root = Path(root).resolve()
    slug_value(slug)
    manifest_path = proof_path(root, slug, "manifest", required=True)
    m = current_manifest(root, slug)
    settings = manifest_config(m)
    evidence = read_json(evidence_path)
    if evidence.get("actor") != "user" or not evidence.get("reviewer") or not evidence.get("environment"):
        raise Invalid("REVIEW: the actual reviewer must be named, actor must be user, and the environment must be completed")
    if not all(evidence["environment"].get(k) for k in ("obsidian", "advanced_canvas", "theme")):
        raise Invalid("REVIEW: Obsidian, Advanced Canvas, and theme versions are required")
    current = hashes(root, artifact_paths(root, slug))
    if evidence.get("artifact_hashes") != current or not artifacts_match_manifest(root, slug, m, current):
        raise Invalid("REVIEW-STALE: manual evidence is not bound to the current file versions; rebuild or update the evidence")
    if evidence.get("presentation_hash") != presentation_identity(root) or m.get("presentation_hash") != presentation_identity(root):
        raise Invalid("REVIEW-STALE: style or tool version changed")
    checks = evidence.get("checks", {})
    if set(checks) != set(visual_checks(settings)) or any(v.get("status") not in ("PASS", "FAIL", "UNKNOWN") or not v.get("evidence", "").strip() for v in checks.values()):
        raise Invalid("REVIEW: every check must record a status and concrete evidence")
    model_path = require_proof_source(root, slug, m["source"])
    if digest(read_json(model_path)) != m["model_hash"]:
        raise Invalid("REVIEW-STALE: model changed")
    validate_bundle(root, read_json(model_path), settings)
    status = "PASS" if all(v["status"] == "PASS" for v in checks.values()) else "FAIL" if any(v["status"] == "FAIL" for v in checks.values()) else "UNKNOWN"
    m["visual"] = {"status": status, "review": evidence, "recorded_at": datetime.now(timezone.utc).isoformat()}
    write_json(manifest_path, m)
    write_text(safe(root, f"note/{slug}/_review-checklist.md"), checklist(slug, status, evidence, settings))
    return {"visual": status, "slug": slug}


def status(root, slug):
    slug = slug_value(slug)
    m = current_manifest(root, slug)
    manifest_config(m)
    current = hashes(root, artifact_paths(root, slug))
    model_path = require_proof_source(root, slug, m["source"])
    stale = not artifacts_match_manifest(root, slug, m, current) or digest(read_json(model_path)) != m["model_hash"] or m.get("presentation_hash") != presentation_identity(root)
    return {"slug": slug, "machine": "STALE" if stale else m["machine"]["machine"],
            "visual": "STALE" if stale else m["visual"]["status"], "artifact_hashes": current,
            "presentation_hash": presentation_identity(root)}
