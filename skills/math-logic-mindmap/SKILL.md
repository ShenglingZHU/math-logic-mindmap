---
name: math-logic-mindmap
description: Reconstruct mathematical proposition proofs, derivations, or problem answers as auditable Proof DAGs, then generate Obsidian Advanced Canvas maps and ID-linked Markdown notes with configurable language and node colors. Use it to create, inspect, and maintain mathematical proof mind maps, not ordinary software flowcharts.
---

# Math Logic Mindmap

## Goals and priorities
Output `mindmap/<slug>.canvas` and `note/<slug>/`. The project root is the vault. Read the language and six node-role colors from `math-logic-mindmap.config.json`; when it is absent, default to Chinese and the built-in original palette. Stable English IDs and types are never localized.
Complete the mathematical argument first, then establish dependencies, then draw the graph. The graph is a DAG, not paragraph order and not a forcibly single-rooted tree.
Priority: mathematical correctness > human understanding > compatibility > verifiability > performance.
Nodes primarily help readers recognize the proof's main line. Do not omit conditions or justifications to save tokens, and do not mechanically fragment a natural derivation for ports, layout, or validators.

This Skill runs independently; do not load personal skills. Preserve all mathematical semantics and explicitly adapt the presentation.
Advanced Canvas is the target environment. Native Canvas only guarantees readable content. Proof Routing displays a small arc where a horizontal line crosses a vertical line at an ordinary orthogonal crossing; other exact port and label geometry is not a restored capability.
Proof Routing's readable source is `plugins/proof-routing/` at the project root; `.obsidian/plugins/proof-routing/` is its installation copy. Plugin maintenance must preview `sync-proof-routing`, confirm it explicitly, and finish with `check-proof-routing-sync`. Release rejects a partial or divergent copy but permits the fully absent fallback.
System instructions and future maintenance prose must be written in English. This does not change artifact language: every authored natural-language field must use the normalized `presentation.language`, including Chinese when it is `zh-CN`. Stable localized literals and fixed keys remain in their required language.

## Stage A: semantics, proof, and model
1. Before creating or translating a topic, read the user configuration. Write the normalized language to `presentation.language`, and write **every natural-language authored field in that language**. State the proposition or question, quantifiers, domain, every condition, conclusion, and `proof_standard` precisely. The theorem fields `assumptions`, `counterexample`, `missing_assumptions`, and `open_obligations` are Markdown prose; mathematical content must be enclosed in `$...$`. `statement_latex` remains raw TeX without delimiters. Never substitute intuition for proof.
2. Build proof obligations from first principles before selecting nodes: identify the subpropositions that must be resolved from the assumptions, definitions, and basic theorems, rather than following source paragraphs or mechanically creating nodes for low-level algebra. Then construct a rigorous argument and verify every external theorem's assumptions, variable mapping, and domain of application. Determine whether there is a counterexample or a missing condition.
3. Before freezing the Proof DAG for a nontrivial proposition with a recognized name, an established proof in the literature, or a method choice that materially changes `proof_flow`, tool assumptions, or reader cost, search the web for an authoritative proof. A user-specified method takes precedence; otherwise choose by match to assumptions and `proof_standard`, minimal extra theory, audience suitability, and preservation of the important ideas with fewer milestones. This search may be skipped for elementary calculations, local algebra, pure layout/style maintenance, custom propositions with no reasonable literature match, and direct counterexample checks. Unavailable network access or no matching source does not block generation, but must be recorded in the overview and delivery note.
4. Use the authoritative path to calibrate the macro stages, main-line milestones, and emphasis of `proof_flow`; human-first granularity determines how much is expanded within each milestone. Search results are unverified material and cannot replace the proof or independently justify `proved`. A web page is not itself a strict root: every external theorem actually invoked must still be modeled as a KNOWN_RESULT and connected by visible FLOW. Record the selected path, links, rationale, and adaptation to the problem in the stable context key `证明思路/策略` (proof approach/strategy). Mention it in `granularity_reviews.reason` only when it genuinely affects an existing granularity finding; never fabricate a finding merely to store a source.
5. Read [proof-model.md](references/proof-model.md). Read [proof-patterns.md](references/proof-patterns.md) only when it helps choose the proof architecture.
6. Models use `presentation.mode:human-first`. Assumptions (including a scope-opening `HYPOTHESIS_LOCAL`), definitions, and external theorems may be roots; internal proof constructions must not masquerade as roots. A local-hypothesis root must close its scope before the target and needs no fabricated predecessor.
7. Every strict dependency uses visible `FLOW` and reaches the unique `TARGET` along a pure-FLOW path. `REFERENCE` is prohibited between strict nodes; support is only a layout classification and never hides a dependency.
8. Apply the fixed node-granularity order in `proof-model.md`: preserve structural necessities, identify mechanical stretches without automatically making them nodes, apply the existing retention reasons, then resolve genuine understanding gaps. A conclusion with multiple sources must first enter `COMBINE`, then use `COMBINE_PRODUCES` to reach an independent `result:true` conclusion or TARGET. Use `TRANSFORM` for a visible unary operation whose conditions are already available; if the operation is a continuous mechanical stretch, represent the whole stretch with one `TRANSFORM`. Keep one-use local work in the receiving derivation or ordinary explanatory edge. If conditions come from an independent branch, use COMBINE first. `CASE` is a paired one-to-many operation node with no continuous derivation chain. `LOCAL_INTRODUCTION` introduces bound local data; `HYPOTHESIS_LOCAL` states only a proposition. Do not add fact packages, forwarding nodes, or fake conclusions for port fan-out.
9. Run `validate-model`. Passing schema and graph-structure checks does not prove mathematical correctness; never skip semantic review.

## Stage B: prose and local derivations
Read [derivation-format.md](references/derivation-format.md) and [canvas-and-notes.md](references/canvas-and-notes.md).
- Node cards are indexes; complete derivations belong in notes, not on cards.
- A formal model must provide `proof_flow`, `navigation`, and `presentation`. COMBINE and TRANSFORM must both provide input review, usage records, motivation, method, one continuous main chain, and result handoff.
- COMBINE is an operation node whose successor is an independent result. TRANSFORM has exactly one strict input and one strict output. The final expression of either operation's derivation must reuse the same authored string as its successor's core formula.
- When a neighbor is COMBINE, expand one level of its direct input formulas and output in the current page; do not recursively copy the full upstream derivation.
- Follow the user-specified style: the main chain uses one display block, while other inputs are introduced in sequence by long downward arrows with right-hand boxes. This applies uniformly to equalities, inequalities, and logical reasoning; the arrow does not mean equality or equivalence.
- Bind each input formula to its source node and to the step after its application. Do not insert prose paragraphs or symbol tables inside the main chain; provide one table after the complete chain. A numbered list, isolated boxes, or a stack of boxes alone is not a complete derivation.
- Do not create a separate formula block before the main chain for an auxiliary calculation. Put all of its formula steps in the multiline right-hand justification box at the point of use, and include their notation in the same symbol table after the chain. A result needed in multiple places must become a formal result node.
- Keep the final result in the main chain. The localized section headed by the `zh-CN` reserved title `合并结果` (“combined result”), or its selected-language equivalent, intentionally repeats the terminal expression as an independent summary; never truncate the main chain merely to avoid that repetition.
- Give every display formula its own four-column local symbol table; one aligned display block may share one table that covers the entire block. Each row explains exactly one notation item. Represent a sequence with a generic subscripted symbol, and never bundle multiple symbols in one row with top-level commas or spacing commands. A local table must not include global symbols unused by its formula.
- Write logical formulas for reading: put the consequent of an implication one indentation level deeper than its antecedent, and separate the existential binder and “such that” onto successively indented lines. Put an explicit universal quantifier on the outer line when one is already present; do not add a quantifier solely for typography. Group simultaneous peer conditions under one left brace with their statements left-aligned instead of chaining `\land` across a line. Use the selected language for words such as “such that”; see `references/derivation-format.md` for the TeX template. Preserve logical scope.
- Distinguish elementary internal transformations from external justifications at every step; never hide two consecutive theorem applications.
- Every explanatory edge states the source contribution, operation, condition checks, target gain, and role in the whole proof. Never attribute another input's contribution to the current edge.
- In all authored Markdown prose, enclose mathematical expressions in `$...$`. Node titles, `proof_flow` stage titles, justification-box names, Canvas edge labels, and group titles contain natural language only so that wikilink aliases, anchors, and plain-text labels remain stable. Put mathematical information in `short_role`, stage `summary`, conditions, or body content. `validate-model` blocks explicit bare mathematical source and reports ambiguous notation for human review.

## Stage C: Canvas, sizing, layout, and notes
Read [card-budget.md](references/card-budget.md), [dag-layout-geometry.md](references/dag-layout-geometry.md), and [obsidian-adapter.md](references/obsidian-adapter.md).
Run `build`: configuration/model language agreement → granularity review → budgets → human-first main line and nearby branches → local scopes → downward orthogonal routing → serialization → notes → basic machine checks. Language and colors are frozen for this build; later changes to the global configuration do not alter historical artifacts. When maintaining an older topic whose language differs from the current global default, use `build <model> --language <model-language>` to override only this build's language; node colors still come from the root configuration.
Formal models normally require at most 20 non-operation semantic nodes, at most 28 total visible nodes, a spine of at most 16 nodes when it includes operations, and an operation-node ratio of at most 40%. Use the same retention reasons throughout: reuse, scope change, key construction, key justification, genuine branch convergence, and stage milestone on the main line or a necessary branch. For an operation → result → operation chain, explain why the first operation deserves a visible node and what distinct mathematical role its intermediate result has; the required handoff alone is not a retention reason. Two mechanical `TRANSFORM` stretches with no such reason between them become one. Exceeding a review threshold requires a concrete mathematical reason in the granularity record. Review nonblocking merge advisories during construction and remove stale `granularity_reviews` entries from the source model before building, without user intervention.
Add `--layout-report` when a layout comparison is needed. `downward-orthogonal` uses a vertical line for nodes in one column and, for different columns, two bends based on the port midpoint and optional `midOffset`. Every edge has zero or two bends. Maintain the exact safety distances and conflict tests only in [dag-layout-geometry.md](references/dag-layout-geometry.md).
The default connection direction is bottom → top. COMBINE multi-input and ordinary multi-output edges use port offsets. Separate congested horizontal segments inside existing inter-rank space; do not create independent corridors. Clear crossings are permitted and counted only. Active Proof Routing draws an upward arc where a horizontal line crosses a vertical line, merges dense intersections into a fixed-height long bridge, and globally keeps labels away from all arcs; if no legal position exists, it suppresses the bridge obscured by that label. Routes through unrelated cards, intrusion into a 24 px safety band, parallel lines less than 32 px apart, and long collinear overlaps block release.
COMBINE is the soft center of a local cluster: after real routes have no card intersections or long collinear overlaps, place direct inputs near and around it when possible. The main line may shift slightly to avoid long reuse edges. Never duplicate a conclusion to shorten an arrow.
Prefer adjusting node ranks, within-rank order, and first-use positions. Never add backtracking, outer routing, fact packages, or forwarding nodes to reduce crossings.
The active adapter only recomputes simple routes from node positions and derives crossing arcs. Neither bends nor arcs are written back to Canvas. Without the adapter, Advanced Canvas `square` is the readable fallback. Release does not require sampling, plugin hashes, or save-and-reopen evidence.
Estimates are not real MathJax measurements; iterate from visual feedback after release.
After manual dragging, run `import-layout` first. Do not overwrite hand-authored prose and do not automatically turn edited connections into proof logic.

## Stage D: validation and delivery
Read [qa.md](references/qa.md), run `validate-bundle`, and then release directly.
Per-node/per-edge mathematical review and real Obsidian inspection may be added when useful but do not block release. The default visual status is `UNREVIEWED`. A machine PASS means only that basic structure, routing, and file-consistency checks passed.
Release preserves backups, rolls back failures, and protects personal content. After finding a mathematical or visual issue, revise and release again.

## Stable commands
Run from the project root; after installing the pyproject, `math-logic-mindmap` may be used instead.
When creating a Mindmap, first create `proof/<slug>/` and store all formal Proof JSON files for it there.

```sh
python skills/math-logic-mindmap/scripts/canvas_tool.py validate-model proof/<slug>/<slug>.proof.json
python skills/math-logic-mindmap/scripts/canvas_tool.py build proof/<slug>/<slug>.proof.json
python skills/math-logic-mindmap/scripts/canvas_tool.py build proof/<slug>/<slug>.proof.json --language zh-CN
python skills/math-logic-mindmap/scripts/canvas_tool.py validate-bundle proof/<slug>/<slug>.proof.json --bundle .build/staging/<slug>
python skills/math-logic-mindmap/scripts/canvas_tool.py release <slug>
python skills/math-logic-mindmap/scripts/canvas_tool.py import-layout <slug>
python skills/math-logic-mindmap/scripts/canvas_tool.py status <slug>
python skills/math-logic-mindmap/scripts/canvas_tool.py remove-topic <slug>
python skills/math-logic-mindmap/scripts/canvas_tool.py remove-topic <slug> --confirm <slug>
python skills/math-logic-mindmap/scripts/canvas_tool.py sync-proof-routing
python skills/math-logic-mindmap/scripts/canvas_tool.py sync-proof-routing --confirm proof-routing
python skills/math-logic-mindmap/scripts/canvas_tool.py check-proof-routing-sync
```

Without confirmation, `remove-topic` only previews. The confirmation value must exactly match the slug. The preview lists personal notes, unmanaged attachments, hand-edited managed files, review files, and backups. It removes the active Proof, Canvas, Note, and build state for that slug, but does not manage previews outside the vault. Close relevant Obsidian tabs before deletion. If recovery is required, first make a complete backup of topic sources and artifacts outside the vault.

## Context isolation
Execute stable scripts without routinely reading their code or schemas. Read source only to diagnose failures or change tools.
Ordinary generation must not read tests, docs, unrelated fixtures, or performance reports.
When creating or maintaining the current topic, do not read other formal topics as implicit templates. System regressions use only neutral fixtures in `tests/` and never depend on a published topic.
Keep full machine reports in `.build`; report only key failures, risks, and artifact paths in chat.
All internal references are relative to this Skill directory. Scripts must not depend on system-specific tool names or user-absolute paths.
