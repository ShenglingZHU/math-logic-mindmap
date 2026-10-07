# Proof Model Protocol

## 1. Ontology
Represent the strict proof as `G=(V,E)` plus theorem metadata. Use node types that express mathematical role rather than visual appearance.

Recommended node types:
- `ASSUMPTION` — explicit hypothesis, domain, regularity, sign/range condition.
- `DEFINITION` — definition or notation that has inferential content later.
- `KNOWN_RESULT` — theorem/lemma/corollary available as an external dependency.
- `CONSTRUCTION` — object deliberately introduced for a constructive argument.
- `CASE` — circular one-input, many-output case operation paired with a `COMBINE`.
- `LOCAL_INTRODUCTION` — rectangular, non-operation node that binds arbitrary data, a fresh witness, or fixed local data.
- `HYPOTHESIS_LOCAL` — temporary local assumption, e.g. contradiction assumption or induction hypothesis.
- `DERIVATION` — substantive transformation or inference.
- `LEMMA` — reusable intermediate proposition established inside this proof.
- `COMBINE` — explicit multi-input composition node that receives two or more predecessor results and derives exactly one successor result. This is the only strict node type allowed to have multiple strict predecessors.
- `TRANSFORM` — explicit unary operation node for differentiation, integration, substitution, normalization, division by a known positive quantity, or elementary simplification after all applicability conditions are already present in its single input context.
- `CONTRADICTION` — explicit inconsistency such as `P ∧ ¬P`, `0<0`, or violation of a standing assumption.
- `BOUND` — established upper/lower bound when this is the main role.
- `EXISTENCE_WITNESS` — constructed object plus verification result.
- `TARGET` — requested final statement.
- `INTUITION` — explanatory content that must not be used as a strict proof dependency.

Type names may be specialized when mathematics benefits, but do not proliferate near-synonyms.

## 2. Project JSON shape
Use `canvas-and-notes.md` and the project schema as the serialization contract.
The logical ontology below is authoritative; note sections use structured prose/formula blocks.
Use label_text only for edge cues; formulas are explained in notes, not MathJax edge labels.
All nodes have sections; all EDGE_DETAIL edges have detail including source_contribution,
transition_steps, conditions/condition_checks, target_gain and role_in_proof.
COMBINE derivation is a list of the same structured blocks.

## 3. Edge semantics
Use edges only for genuine inferential dependence. Suggested relations:
- `REQUIRED_FOR` — target step cannot be justified without source result.
- `APPLIES_THEOREM` — source is a theorem/definition/tool whose content is invoked at target.
- `VERIFIES_CONDITION` — source establishes a hypothesis needed by a theorem used at target.
- `FEEDS_CASE` — one structural partition input to `CASE`.
- `CASE_BRANCH` — labeled explanatory edge from `CASE` to the first substantive rectangle of one case.
- `OPENS_SCOPE` — unlabeled structural edge from a local introduction into its child scope.
- `FEEDS_COMBINE` — source supplies one required mathematical input to a `COMBINE` node.
- `COMBINE_PRODUCES` — the `COMBINE` node has completed the multi-input derivation and produces its single successor result.
- `FEEDS_TRANSFORM` / `TRANSFORM_PRODUCES` — the single input and output edges of a unary `TRANSFORM`; both are unlabeled `STRUCTURAL_ONLY` edges.
- `DISCHARGES` — explanatory edge closing one local scope by a declared rule; it records generalized variables and discharged hypotheses separately.
- `ESTABLISHES_TARGET` — immediate high-level support for the target.

Do not use an edge merely because one paragraph appears before another.


### 3A. Edge identity, detail mode, and label semantics
Every displayed edge must have a unique stable `id` (for example `E1`, `E2`, ...). The edge ID is used by geometry, label ownership, interaction, and QA.

Every edge must also declare one of two semantic presentation modes:
- `EDGE_DETAIL` — this arrow owns standalone explanatory content that can be opened through both endpoint notes;
- `STRUCTURAL_ONLY` — this arrow exists to show dependency/routing structure but owns no standalone detail-note edge explanation.

The visual contract is intentionally bidirectional:

`EDGE_DETAIL` **iff** one concise visible label is rendered on/adjacent to that arrow.

Therefore:
- every `EDGE_DETAIL` edge must have a non-empty `label_text` (project labels are plain text; no `label_latex`), plus non-empty edge `detail` data;
- every `STRUCTURAL_ONLY` edge must have no visible label and no standalone `detail` content;
- an elementary unary operation that deserves a visible node uses `TRANSFORM`; a one-input logical implication between ordinary strict nodes remains `EDGE_DETAIL`;
- predecessor → `COMBINE` `FEEDS_COMBINE` edges are normally `STRUCTURAL_ONLY`: they simply deliver inputs to the COMBINE node, whose node detail owns the actual multi-input synthesis. This is the canonical unlabeled-arrow case;
- a `COMBINE_PRODUCES` edge is normally `STRUCTURAL_ONLY` when the COMBINE node already explains the synthesis and the successor node explains the result; it may be `EDGE_DETAIL` only when there is genuinely distinct edge-specific reasoning that does not duplicate either node;
- if a structural edge is promoted to have its own detail-note explanation, it must simultaneously be promoted to `EDGE_DETAIL` and receive a concise visible label. Hidden edge explanations behind unlabeled arrows are prohibited.

Node-owned reading context is distinct from an independent edge derivation: COMBINE `input_review` and `output_handoff`, or a receiver's `input_context`, describe delivered content and its use. Both endpoint notes reuse that single source. They do not create an edge note, label, or new mathematical operation, and do not promote a STRUCTURAL_ONLY edge. EDGE_DETAIL context reuses its existing source_contribution/target_gain.

Label content rules:
- the label is semantically owned by exactly that edge ID;
- it names the local operation/relation in the shortest useful phrase, normally a compact verb/noun phrase rather than a sentence;
- in `zh-CN`, prefer specific cues such as `积分` (integration), `代入` (substitution), `取对数` (take logarithms), or `应用 Itô 引理` (apply Itô's lemma) over vague text such as `处理` (process), `推导` (derive), or `得到` (obtain) when a more precise operation is known; apply the same rule in every selected language;
- the label is a cue; the detailed derivation, assumptions, and justification stay in `detail`;
- do not use one floating label to describe several neighboring edges;
- when the same phrase applies to several edges, repeat separate labels attached to their respective edge IDs or model the shared concept as an explicit mathematically meaningful node;
- label placement is a rendering concern, but the semantic ownership (`edge_id -> label`) must already be unambiguous in the Proof Model.

Correct data binding alone is insufficient: the final rendered label must also satisfy the geometry-level ownership-halo rules.

## 4. Construction algorithm
### Pass A — theorem normalization
Extract:
- quantifiers;
- domains;
- all assumptions;
- exact target;
- proof standard;
- whether the user expects one proof or alternative proofs.

`statement_latex` stores raw TeX without delimiters. `assumptions`, `counterexample`,
`missing_assumptions`, and `open_obligations` are Markdown prose: wrap every mathematical
expression in `$...$` so prose and formulas can be mixed without renderer inference.
`formula_latex` is the complete mathematical proposition used by proof references and
generated notes. The optional `card_formula_display` is `full` (the default) or
`summary`; `summary` omits only the card formula when its complete form exceeds the
card budget. It never supplies an alternate mathematical formula. Author multiline
logical propositions using the template in `derivation-format.md`.
Do not put `$...$` in node titles, `proof_flow` stage titles, continuous-chain basis
names, Canvas edge labels, or scope titles; those link-, anchor-, or literal-text fields
use short natural-language wording. Put mathematical detail in `short_role`, stage
`summary`, conditions, or prose instead.

### Pass B — proof skeleton
Before low-level algebra, derive likely high-level obligations from the statement, definitions and basic results: subclaims, directions, cases, bounds, witness verification, contradiction target, induction base/step, etc. This is the first-principles pass; do not turn the paragraph order of a reference or every algebraic rewrite into nodes.

For a named theorem, a nontrivial proposition with an established literature proof, or a problem whose method choice materially changes `proof_flow`, assumptions or reader cost, search for at least one authoritative proof before freezing the skeleton. Prefer original papers, established textbooks, professional societies and university course material; AI-generated pages, content farms, anonymous answers and unreviewed posts cannot be the sole authority. Skip this search for routine calculations, local algebra, layout-only maintenance, direct counterexample checks, or bespoke claims with no reasonable literature analogue.

An authoritative path governs the macro structure: use it to calibrate `proof_flow` stages, mainline milestones and emphasis. Human-first granularity governs how much explanation is expanded inside each milestone. If the source omits a condition check the intended reader needs, expand it inside the relevant note unless it is an independent branch or reusable result. The source's paragraphs do not dictate nodes.

When several authoritative paths exist, first follow an explicitly requested method; otherwise choose by exact match to the hypotheses and `proof_standard`, avoidance of unnecessary machinery, audience fit, and the smallest milestone set that preserves the theorem's real focus. Keep unrelated alternative proofs in separate models. Persist the selected path, links, rationale and adaptation in `context["证明思路/策略"]`; mention a source in an existing `granularity_reviews[].reason` only when it actually explains that merge/retain decision. If network access or a suitable source is unavailable, record that fact and continue from first principles.

### Pass C — rigorous derivation
Solve each obligation. For every named theorem/tool, record:
1. theorem statement or relevant clause;
2. hypotheses;
3. mapping from theorem variables/objects to current objects;
4. proof-model nodes or complete derivation steps that verify hypotheses; an independent proof branch remains a visible FLOW input;
5. conclusion gained.

### Pass D — dependency extraction
For each established result, ask: “Which facts are logically necessary to justify this result?” Every strict dependency is a visible `FLOW` edge. Ordinary results have strict indegree at most one; two or more independent sources must first enter a `COMBINE`, whose sole successor is the separately stated result or TARGET.

Immediately classify every edge's presentation semantics:
1. ordinary one-input non-COMBINE transition → `EDGE_DETAIL` + concise label + detail-note detail;
2. structural feed/hand-off with no independent reasoning content → `STRUCTURAL_ONLY` + no label + no edge detail;
3. if any edge later receives standalone detail-note explanation, its mode must be `EDGE_DETAIL` and its visible label becomes mandatory.

### Pass E — granularity / semantic-atomicity review
Choose the coarsest card that still exposes the proof's real milestones. Apply this order before drawing the graph:
1. Keep structural necessities: assumptions, definitions, external `KNOWN_RESULT` nodes actually invoked, `COMBINE`, `CASE`, `TARGET`, scope openings and closures, and explicit `CONTRADICTION` nodes in reductio. Use the existing scope edges and nodes; keep the independent result after `COMBINE` or `TRANSFORM`. An external theorem always has a visible `FLOW` dependency.
2. Identify each continuous stretch of mechanical expansion, rearrangement, cancellation, or substitution. First decide whether the stretch deserves a visible node under steps 3–4. If it does, use one `TRANSFORM` with every formula step in its continuous chain. If it does not, keep the work in the receiving node's derivation or an ordinary `EDGE_DETAIL.detail.transition_steps`. A simplification serving only the current line of another node's derivation stays there. An important external-theorem application is not a mechanical step. A reused intermediate line breaks the stretch and becomes an independent result; two adjacent `TRANSFORM` stretches with no reason to retain their intervening result become one stretch. Independent side conditions enter through `COMBINE` before a unary `TRANSFORM`.
3. Apply the existing retention reasons, consistently named here: reuse, scope change, key construction, key justification, genuine branch convergence, and stage milestone. A result used in two or more downstream places must be a node. Mere novelty is insufficient: a new result counts only when used beyond the immediately following step or when the intended reader needs to remember it as a stage result. A milestone may be on the main line or a necessary branch. A key insight belongs under key construction, key justification, or stage milestone according to its mathematical role. Proof-mode changes use the existing scope and case structure. An invoked external theorem is already its own node; do not add a separate “apply theorem” node. A change of object or method alone is not an additional retention category.
4. For a remaining understanding gap, escalate only as far as needed for learners with low mathematical fluency. Continue the derivation first; state a needed basis in the available justification or condition-check field; explain motivation in an existing explanatory edge or node motivation field; create a node only for a key insight or a result used later. “A reader might be confused” alone does not justify another node. This sequence is semantic, not a requirement that every location support every visual device.

For an ordinary one-input edge, put local work in `detail.transition_steps`, checks in `detail.condition_checks`, and motivation in `detail` or the receiver's `navigation.motivation`; its existing `label_text` remains a short cue. For `COMBINE`/`TRANSFORM`, use the continuous main chain, a right-hand box when an actual basis enters, and `combine_motivation`/`transform_motivation` to explain why. Their structural input/output edges remain unlabeled. Do not promote an independent side condition into a unary operation merely to gain a box.

Neutral comparisons: a one-use expansion immediately consumed by a result stays in that result's derivation or the ordinary explanatory edge. A visible sequence of expansion, substitution, and simplification on one already justified input uses one `TRANSFORM`, not three. If its substitution result feeds a second branch, make that intermediate result visible and split the operation there. A theorem plus separately established applicability conditions enters `COMBINE` and yields its independent conclusion; the theorem node is retained, but no extra “apply theorem” node is added.

Map the chosen macro path to project roles before layout: `proof_flow` holds its stages; `result:true` marks a reader-visible stage result that downstream work actually receives; `LEMMA` is reserved for a reusable or independently important proposition; `DERIVATION` holds a substantive local inference; and `COMBINE` appears only where genuine independent inputs meet. A retrieved page is not a strict root. Only an external mathematical result actually invoked by the proof becomes a `KNOWN_RESULT`, after its assumptions and variable mapping are independently checked.

For **every node**, identify its single subject/theme and semantic nucleus. Split the node when it conceals independent logical actions, distinct theorem applications, reusable lemmas, changes of proof mode, distinct mathematical objects, or multiple conclusions. Keep each invoked external theorem as a `KNOWN_RESULT`; where its independent conditions join it, use `COMBINE` and its independent result rather than another application node. Titles/body text shaped like “A 与 B”, “A 和 B”, “A、B 和 C”, “A, B and C”, or equivalent coordinated lists are an explicit review trigger: if the coordinated items can be stated, justified, inspected, or reused independently, they belong in separate nodes.

A conjunction may remain only when it denotes one indivisible mathematical concept/object/atomic statement and decomposition would distort the meaning. Do not use this exception to hide several claims in one rectangle. If several atomic nodes jointly establish a later result, preserve them as separate predecessors and synthesize them through the required `COMBINE` node. Do not coalesce away a required COMBINE node.

### Pass F — topological audit
The strict subgraph must be acyclic. If a cycle appears, either the proof is circular or one node has been defined at the wrong abstraction level. Repair the mathematics/model before layout.

## 5. Root selection
A root is a strict-proof node with no strict predecessor. Valid roots include assumptions, scope-opening local hypotheses, definitions, axioms, and known results. Multiple roots are normal.

Do not merge independent roots into a synthetic START node unless the combined statement itself has mathematical meaning (e.g. a named hypothesis package explicitly used as one object).

## 6. COMBINE selection
COMBINE is the visible synthesis operation and is followed by exactly one independent `result:true` conclusion or TARGET. Formula equality across that handoff is intentional. Never add it merely to increase port capacity or satisfy a layout validator. A paired case COMBINE uses `combine_reason:"case_reconciliation"` and one `case_closures` record per CASE branch. Each record names the branch edge, `rule:"case_reconciliation"`, generalized binding IDs, and discharged case-condition edge IDs. A finite branch discharges its own CASE_BRANCH condition; an indexed branch generalizes its arbitrary index and records no discharged case condition. Its `scope_closures` record uses the same generalized IDs. An induction COMBINE uses `combine_reason:"induction"` and records base IDs, a nonempty list of directly discharged step IDs, and the principle ID; all listed nodes directly feed that COMBINE.

Structural invariants:
- `COMBINE` strict indegree: at least 2;
- `COMBINE` strict outdegree: exactly 1;
- every non-COMBINE strict node indegree: at most 1;

The COMBINE detail must record enough information to reconstruct the synthesis, preferably `combine_inputs`, `combine_output_latex`, and a non-empty `derivation`. Do not create COMBINE for a one-input elementary rewrite.


## 6A. COMBINE detail semantics
The COMBINE node is intentionally separate from its successor result node.

COMBINE detail-note content should contain:
- predecessor node IDs/titles and their relevant formulas;
- local goal: the formula/statement to be produced;
- stepwise synthesis, including substitutions and compatibility conditions;
- named external facts and condition checks where needed;
- final formula identical to the successor node's core formula or statement;
- concise validation of why the stitching is legitimate.

Format nontrivial synthesis with `references/derivation-format.md`.

The reading and continuous-chain contract in `canvas-and-notes.md` is mandatory. Each input_review binds a predecessor reference and contribution. Each input_usage binds a concrete expression/application row in derivation_chain: one start supplies the first expression; every other input enters via a long downward arrow with its actual basis boxed to the right, between the before/after expressions. This applies to equality, inequality and logical inference without changing their mathematical relations. One display and one local symbol table cover the whole main chain. The chain ends at combine_output_latex, identical to the successor core formula; the `zh-CN` reserved heading `合并结果` (“combined result”), or its selected-language equivalent, intentionally repeats this terminal result as a separate summary. Auxiliary conclusions must be explicitly reintroduced into the main chain. Mathematical review verifies application, not merely presence.

The successor/result node must not duplicate this derivation. Explain instead the successor formula itself: mathematical role/status, domain, properties, interpretation, consequences, and downstream use.

## 7. Strict vs explanatory layers
`INTUITION`, examples, geometric pictures, numerical checks, and informal motivations are valuable but must be visibly distinct from strict proof nodes. They may annotate strict nodes but cannot serve as logical predecessors of a strict conclusion.

## 8. False or under-specified claims
If the target is false:
- set theorem status to `refuted`;
- construct a counterexample dependency graph when helpful;
- do not create a fake TARGET marked proved.

If the target is true only under missing conditions:
- set status to `needs_assumption`;
- identify the missing assumption;
- if helpful, provide a corrected theorem and prove that corrected version, clearly separated from the original claim.

## 9. Symbol discipline
Global legend: recurring objects/operators/constants.
Local notes: temporary variables, branch-specific symbols, substitutions, witness definitions.

`LOCAL_INTRODUCTION`, `CONSTRUCTION`, and `EXISTENCE_WITNESS` bind symbols with stable IDs, TeX spelling, range, and dependencies. Every strict node and every explanatory edge declares its free local uses in `uses_symbols`; construction dependencies are included there. An operation immediately producing a construction result may introduce that result's symbols in its own derivation; no earlier node may use them. Global legend rows reserve their spelling unless a `binding_ref` identifies a local binding. Formula-table rows referring to a local binding carry its `binding_ref`; an unreferenced row matching a local spelling produces a warning. Visibility, freshness among simultaneously visible binders, and dependency order are machine-checked; correctness of the authored formulas and their symbol declarations remains a mathematical review obligation.

Always define potentially ambiguous notation such as transposes, gradients, expectations, norms, asymptotics, measure notation, branch-specific indices, or overloaded operators when first used in a pedagogically meaningful place.

## 10. Per-formula symbol annotations
Use formula blocks `{kind:"formula",latex:"...",symbols:[...]}` inside sections or derivation.
Each symbols row has symbol_latex, definition_role, range_unit, interpretation.
Each row explains exactly one notation item. Prefer `I`, `f`, `x_i`, `\lambda_i` or `P(k)`; write a family as `\lambda_i`, not `\lambda_1,\dots,\lambda_n`. Top-level lists such as `I,f,n`, `x,y` or `I\quad f\quad n` are prohibited. A separator inside a subscript or balanced argument, such as `x_{i,j}` or a genuinely defined `P(A\mid B)`, is not by itself a list. Do not mechanically split a batch while copying one vague explanation to every row.
The validator rejects only unambiguous top-level separators. Ordinary TeX spaces do not reliably identify symbol boundaries, so batches such as `I f n` remain an explicit human-review item rather than a hard parsing rule.
One multi-line aligned display block owns one four-column local table; every independent
display block owns another. Inline mathematics does not create an artificial table.
The exact `zh-CN` headers are `符号`, `数学定义或角色`, `取值范围 / 单位`, and `实际含义 / 物理解释（如适用）` (four columns; slashes inside header names are literal text). Other languages use their catalog equivalents. No serial-number column.
Cover all meaningful notation used by that block, never unrelated global symbols.
Do not fabricate units, domains, or physical interpretation. In `zh-CN`, give `不适用` (“not applicable”) when appropriate; use the corresponding natural-language value in other model languages.
The global symbol legend never substitutes for any local formula's table.
Build each local table from the notation actually present in its formula and preserve first-use order.
Render through Obsidian MathJax; use semantic TeX commands for bars inside tables.
Project CSS allocates a compact symbol column and readable wrapped prose columns;
actual width/font-size/overflow remains an Obsidian review item, not an estimated PASS.
