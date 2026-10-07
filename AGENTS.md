# Math Logic Mindmap Project

## Tasks and authoritative source
When a request involves a mathematical proof, derivation, proposition explanation, problem answer, or mind-map edit, load
`skills/math-logic-mindmap/SKILL.md`. It is the complete specification; `.agents/skills` and
`.claude/skills` are generated discovery entry points only. Claude also reads `CLAUDE.md`.

The user's current requirements take precedence. Preserve the complete mathematical and logical specification; adapt presentation according to the project's Canvas rules.
Priority: mathematical correctness > human understanding > compatibility > verifiability > performance.
Keep the model's “multiple roots converging level by level to one target” structure and human-first granularity: do not omit proof conditions or local symbol tables, and do not create fact packages, forwarding nodes, or duplicate mathematical conclusions for ports, layout, validators, or token cost. The required COMBINE → independent result pattern is not an erroneous duplication.

## Project boundaries
- Treat the project root as the Obsidian vault. Read the prose language and six node-role colors from `math-logic-mindmap.config.json`; when the file is absent, default to Chinese and the original palette. Keep types and IDs as stable English markers.
- System files and all future system-file maintenance must be written in English, except `README.md`, `docs/README.fr.md`, and `docs/README.zh-CN.md`, which are equivalent English, French, and Chinese user guides. This maintenance language is independent of the configured mind-map language: every authored natural-language field and generated artifact must still use the normalized `presentation.language` (for example, Chinese when it is `zh-CN`). Stable localized literals and fixed keys remain in their required language.
- Store each Mindmap's formal Proof files in `proof/<slug>/`; the model path is `proof/<slug>/<slug>.proof.json`. Deliverables remain `mindmap/<slug>.canvas` and `note/<slug>/`.
- When creating or maintaining a topic, do not use other formal topics as implicit templates. Ordinary system tests must not read formal topic content from `proof/`, `mindmap/`, or `note/`.
- Advanced Canvas is the target environment; exact port, route, and focus interactions from reference HTML are outside the Canvas contract.

## Execution
Complete the mathematical argument before drawing the graph. Read the references stage by stage according to Skill Stages A–D.
Graphs use the human-first Proof model. Strict roots may only be assumptions (including a scope-opening `HYPOTHESIS_LOCAL`), definitions, or external theorems. A local-hypothesis root must close its scope before the TARGET; never invent an incoming dependency for it. Every strict dependency must enter the unique TARGET through a visible FLOW edge; REFERENCE is prohibited between strict nodes. A conclusion with multiple sources must first converge through COMBINE and then enter an independent result node. A simple unary operation whose conditions are already available may use TRANSFORM.
COMBINE and TRANSFORM notes both use one continuous formula chain with right-hand justification boxes. TRANSFORM does not accept independent side-condition inputs; use COMBINE first when an independent branch is required. Even an external theorem listed in `presentation.support` must retain a visible FLOW edge.
Execute stable scripts instead of routinely reading source code; read code only while debugging.
Ordinary generation must not load tests, docs, or unrelated reports. Use Python 3.11+ and jsonschema.

```sh
python skills/math-logic-mindmap/scripts/canvas_tool.py --help
python skills/math-logic-mindmap/scripts/canvas_tool.py validate-model proof/<slug>/<slug>.proof.json
python skills/math-logic-mindmap/scripts/canvas_tool.py build proof/<slug>/<slug>.proof.json
python skills/math-logic-mindmap/scripts/canvas_tool.py release <slug>
python skills/math-logic-mindmap/scripts/canvas_tool.py remove-topic <slug>
python -B -m unittest discover -s tests -v
```

Machine structure checks do not prove mathematical correctness automatically, but a graph may be released once the basic model, artifact, and file-safety checks pass. Mathematical review and a real Obsidian visual inspection are optional later feedback, not release gates.
All routes use the `downward-orthogonal` profile; see `references/dag-layout-geometry.md` in the Skill for the complete geometry rules.
Clear arrow crossings are allowed. Do not create outer corridors, upward backtracking, or extra mathematical nodes merely to remove crossings. A route through an unrelated card or a long collinear overlap still blocks release.
The default visual status is `UNREVIEWED`, which does not block release; continue adjusting after a problem is found. A known mathematical gap must never be marked `proved`.

## File safety and maintenance
Use UTF-8 without BOM and LF line endings. Serialize JSON through a serializer. Use complete vault-relative paths with forward slashes in links.
Never silently overwrite hand-authored content. Use `import-layout` for layout changes and preserve personal-note regions.
Run the relevant regressions after changing tools. Generate the Skill entry points with `sync-skills` and verify them with `check-skill-sync`.
Proof Routing has one readable source at `plugins/proof-routing/`; `.obsidian/plugins/proof-routing/` is an installation copy. Preview `sync-proof-routing`, confirm it explicitly, and run `check-proof-routing-sync` after changing the plugin. A release rejects a partial or divergent installation copy but still permits the fully absent fallback.
The project runs without Git; do not initialize Git without being asked.
