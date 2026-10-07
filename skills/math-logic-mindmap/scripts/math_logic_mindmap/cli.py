from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__
from .bundle import (build, current_manifest, import_layout, manifest_config, proof_path,
                     record_review, release, remove_topic, status, validate_bundle)
from .common import Invalid, digest, read_json, safe, slug_value, write_json, write_text
from .i18n import visual_checks
from .model import validate
from .routing import proof_routing_sync_report, sync_proof_routing


def root_path(value):
    if value:
        return Path(value).resolve()
    here = Path.cwd().resolve()
    for p in (here, *here.parents):
        if (p / "skills/math-logic-mindmap/SKILL.md").is_file():
            return p
    raise Invalid("Cannot find the project root; pass --root")


def entry_text():
    return """---
name: math-logic-mindmap
description: Reconstruct mathematical proofs, proposition explanations, derivations, or problem answers as auditable Obsidian Canvas maps and linked notes with configurable language and node colors. Also use it to maintain existing proof mind maps. Do not use it for ordinary software mind maps.
---

# Project Skill Entry Point (Generated)

First locate the project root containing AGENTS.md and skills/math-logic-mindmap.
Read `skills/math-logic-mindmap/SKILL.md` at that root in full and follow its Stages A–D.
Resolve all references, schemas, and scripts relative to the complete Skill directory; do not look for them relative to this entry point.
Do not treat this entry point as the complete specification.
Use `sync-skills` to update entry points. Edit mathematical rules only in the complete Skill and its references.
Write system instructions and future system-file maintenance prose in English. Continue to write every authored mind-map field in the normalized `presentation.language`.
"""


def sync_skills(root, check=False):
    paths = [".agents/skills/math-logic-mindmap/SKILL.md", ".claude/skills/math-logic-mindmap/SKILL.md"]
    expected = entry_text()
    mismatches = []
    for p in paths:
        f = safe(root, p)
        if check:
            if not f.exists() or f.read_text(encoding="utf-8") != expected:
                mismatches.append(p)
        else:
            if not f.exists() or f.read_text(encoding="utf-8") != expected:
                write_text(f, expected)
    if mismatches:
        raise Invalid("SKILL-SYNC: " + ", ".join(mismatches))
    return {"skill_sync": "PASS"}


def status_report(root, slug):
    result = status(root, slug)
    slug = slug_value(slug)
    manifest = current_manifest(root, slug)
    model_stale = digest(read_json(proof_path(root, slug, "proof", required=True))) != manifest["model_hash"]
    review = manifest.get("mathematical_review")
    if not isinstance(review, dict):
        review_status = "UNREVIEWED"
    elif model_stale or review.get("model_hash", manifest["model_hash"]) != manifest["model_hash"]:
        review_status = "STALE"
    else:
        review_status = review.get("status", "UNREVIEWED")
    return {**result, "mathematical_review": review_status}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Math Logic Mindmap: generation, validation, layout import, and layered review")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--root", help="project/vault root; by default, search upward from the current directory")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate-model", "build", "validate-bundle"):
        p = sub.add_parser(command)
        p.add_argument("model")
        if command == "build":
            p.add_argument("--relayout", action="store_true", help="explicitly ignore the manual layout for this build")
            p.add_argument("--layout-report", action="store_true", help="write layout metrics and a schematic SVG that is not an actual routed rendering")
            p.add_argument("--language", help="override only this build's language; colors still come from the root configuration")
        if command == "validate-bundle":
            p.add_argument("--bundle", help="another vault root to inspect; defaults to the project root")
    for command in ("release", "import-layout", "status"):
        p = sub.add_parser(command); p.add_argument("slug")
    p = sub.add_parser("remove-topic")
    p.add_argument("slug")
    p.add_argument("--confirm", help="must exactly match the slug; omit for preview only")
    p = sub.add_parser("record-review"); p.add_argument("slug"); p.add_argument("evidence")
    p = sub.add_parser("review-template"); p.add_argument("slug"); p.add_argument("output")
    p = sub.add_parser("export-preview"); p.add_argument("slug"); p.add_argument("destination")
    sub.add_parser("sync-skills")
    sub.add_parser("check-skill-sync")
    p = sub.add_parser("sync-proof-routing")
    p.add_argument("--confirm")
    sub.add_parser("check-proof-routing-sync")
    args = parser.parse_args(argv)
    try:
        exit_code = 0
        root = root_path(args.root)
        cmd = args.command
        if cmd == "validate-model":
            model = read_json((root / args.model).resolve())
            info = validate(model)
            result = {"schema": "PASS", "structure": "PASS", "model_hash": digest(model), "warnings": info["warnings"],
                      "quantifier_order": info["quantifier_order"]}
        elif cmd == "build":
            result = build(root, root / args.model, args.relayout, args.layout_report, args.language)
        elif cmd == "validate-bundle":
            result = validate_bundle(Path(args.bundle).resolve() if args.bundle else root, read_json(root / args.model))
        elif cmd == "release":
            result = release(root, args.slug)
        elif cmd == "import-layout":
            result = import_layout(root, args.slug)
        elif cmd == "record-review":
            result = record_review(root, args.slug, root / args.evidence)
        elif cmd == "status":
            result = status_report(root, args.slug)
        elif cmd == "remove-topic":
            result = remove_topic(root, args.slug, args.confirm)
            exit_code = 1 if result.get("status") == "FAIL" else 0
        elif cmd == "review-template":
            s = status(root, args.slug)
            checks = visual_checks(manifest_config(current_manifest(root, args.slug)))
            output = safe(root, args.output)
            if output.exists():
                raise Invalid("The evidence-template target already exists and will not be overwritten")
            write_json(output, {"actor": "user", "reviewer": "Enter the actual reviewer", "environment": {"obsidian": "Enter the version", "advanced_canvas": "Enter the version", "theme": "Enter the default light/dark themes and versions"},
                "artifact_hashes": s["artifact_hashes"], "presentation_hash": s["presentation_hash"],
                "checks": {k: {"status": "UNKNOWN", "evidence": v} for k, v in checks.items()}})
            result = {"template": str(output), "visual": "UNKNOWN"}
        elif cmd == "export-preview":
            slug_value(args.slug)
            dest = Path(args.destination).resolve()
            if dest.is_relative_to(root) or dest.exists():
                raise Invalid("The preview directory must be outside the project vault and must not already exist")
            stage = safe(root, f".build/staging/{args.slug}")
            model = read_json(stage / "model.json")
            validate_bundle(stage, model)
            dest.mkdir(parents=True)
            for folder in ("mindmap", "note"):
                shutil.copytree(stage / folder, dest / folder)
            css = root / ".obsidian/snippets/math-logic-mindmap.css"
            if css.exists():
                out = dest / ".obsidian/snippets"; out.mkdir(parents=True); shutil.copy2(css, out / css.name)
            result = {"preview_vault": str(dest), "visual": "UNREVIEWED"}
        elif cmd == "sync-proof-routing":
            result = sync_proof_routing(root, args.confirm)
        elif cmd == "check-proof-routing-sync":
            result = {"action": "check-proof-routing-sync", **proof_routing_sync_report(root)}
            exit_code = 1 if result["status"] == "FAIL" else 0
        else:
            result = sync_skills(root, check=cmd == "check-skill-sync")
        # Warnings are summarized on console; full build report retains all items.
        result = dict(result)
        if isinstance(result.get("warnings"), list) and len(result["warnings"]) > 8:
            result["warning_count"] = len(result["warnings"])
            review = [w for w in result["warnings"] if w.startswith("GRANULARITY-REVIEW:")]
            other = [w for w in result["warnings"] if not w.startswith("GRANULARITY-REVIEW:")]
            result["warnings"] = sorted(
                other, key=lambda warning: not warning.startswith("MATH-INLINE-RISK")
            )[:max(0, 8 - len(review))] + review[:8]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return exit_code
    except (Invalid, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
