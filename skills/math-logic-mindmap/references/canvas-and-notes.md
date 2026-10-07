# Canvas and Notes Contract

## Model and file interface
Formal models follow the project schema. A slug matches `[a-z0-9]+(-[a-z0-9]+)*`. Use a theorem's conventional English name, or a concrete descriptive short English name for an ordinary problem.
The agent names it from semantics and never applies irreversible automatic Chinese-to-pinyin conversion. A name remains stable after first write; distinguish different entities with qualifiers instead of overwriting a graph with the same name.
Node IDs use forms such as A1/N1/C1/T1 and contain no hyphen. E is reserved for edges and G/UI for display elements.
Node and edge IDs are case-insensitively unique within one model. IDs may repeat across models, but every link includes the complete `note/<slug>` path.

The project schema is at `../scripts/math_logic_mindmap/schemas/proof-model.schema.json`. A formal model contains `theorem`, `context`, `symbols`, `scopes`, `nodes`, `edges`, `target_id`, `proof_flow`, and `presentation`. `presentation.language` is required and may be `zh-CN`, `en`, or `fr`; `build` requires it to match the user configuration.
`theorem` contains `title`, `statement_latex`, `assumptions`, `proof_standard`, and `status`. `statement_latex` is raw TeX without delimiters. `assumptions`, `counterexample`, `missing_assumptions`, and `open_obligations` are Markdown prose whose mathematical expressions are enclosed in `$...$`.
`context` has exactly six stable internal keys: `领域` (field), `背景` (background), `角色 / 重要性` (role/importance), `作用` (purpose), `证明思路/策略` (proof approach/strategy), and `证明工具` (proof tools). These literal keys never change with output language; their values and rendered headings use the model language.
`nodes` retain logical types and readable summaries, while `sections` contain complete content. COMBINE additionally has `combine_inputs`, `combine_output_latex`, and `derivation`.
`edges` retain `id/source/target/relation/detail_mode`. EDGE_DETAIL uses plain-text `label_text` and `detail`.
`detail` contains `summary`, `source_contribution`, `transition_steps`, `target_gain`, `conditions`, `condition_checks`, and `role_in_proof`, and may contain `sections`.

## Human-first presentation interface
`presentation` contains `mode:"human-first"`, a vertical `spine`, nearby `branches`, card-referenced `support`, non-proof `examples`, and `granularity_reviews`. Every node belongs to exactly one of these.

Every edge also has `display_mode`. Strict nodes may be connected only by `FLOW` edges that enter Canvas; `REFERENCE` serves only supplementary material outside the strict proof. Every strict node must reach the unique TARGET by a pure-FLOW path.

A multi-input ordinary node uses `inference`: list the input nodes, source formulas, contributions, usage steps, and start/basis/condition roles exactly, then provide motivation, method, a continuous derivation chain, and result handoff. The chain's final formula must equal the node's core formula.

Every build generates `reports/granularity.json`. Its `findings` and `unresolved` retain the blocking checks for budgets, operation ratio, adjacent duplicate formulas, and operation → result → operation chains. Each unresolved finding blocks release. Its separate `advisories` identify one-input/one-output ordinary results for a semantic deletion test; they do not block release or claim that deletion is valid. The current candidate types are `DERIVATION`, `LEMMA`, and `BOUND`; evaluate any future specialized type explicitly before adding it. Review each candidate during construction. If it is retained, use `presentation.granularity_reviews` with `decision:"retain"` and a concrete reason from reuse, scope change, key construction, key justification, genuine branch convergence, or a stage milestone on the main line or a necessary branch. A live finding or candidate with `decision:"merge"` has not been merged; remove the node and repair its dependencies instead. `stale_reviews` lists review IDs no longer matching a live finding or advisory. Unreviewed candidates and stale reviews produce one nonblocking warning in validation, build, and release summaries; the author removes stale entries from the source model before building. Validation and build never rewrite that source.

## Structured content
`sections` is a list of `{heading, blocks}`. A block has one of two forms:
- `{kind:"prose", text:"中文说明，可使用 $x$ 行内公式"}` — an intentional `zh-CN` authored-content example.
- `{kind:"formula", latex:"不含 $$ 的 TeX", symbols:[...]}` — an intentional example meaning TeX without `$$`.
A symbol row contains `symbol_latex`, `definition_role`, `range_unit`, and `interpretation`.
Each row explains exactly one notation item. Represent a sequence with a generic subscript such as `\lambda_i`. Top-level bundles such as `I,f,n`, `x,y`, and `I\quad f` are prohibited. A comma within the subscript of `x_{i,j}`, or inside a genuinely single definition such as `P(A\mid B)`, does not cause a split. A local table contains only notation actually used by its formula and never copies the full global table.
Put display formulas only in formula blocks; do not hide `$$` or backslash display delimiters in prose, `transition_steps`, or condition descriptions.
Every mathematical variable in prose must use explicit inline mathematics; do not rely on Unicode to imitate MathJax.
There are three rendering contexts. Markdown fields use `$x$`. Continuous-chain justification names enter TeX `\\text{}` and contain natural language only. Node titles and `proof_flow` stage titles enter wikilink aliases or anchors, while Canvas edge labels and scope titles are plain text; all of these also contain natural language only. Non-Markdown fields must not contain `$x$`, `x_i`, or other formula source. Move mathematical detail needed by a title into `short_role`, the stage `summary`, conditions, or body content.
For example, a Chinese assumption may be ``$n\\ge1$，且 $x_i\\in I$``, not ``n\\ge1``, ``x_i∈I``, or a Unicode mathematics string. Explicit bare formulas trigger `MATH-INLINE`; ambiguous cases such as an isolated Latin letter in Chinese produce a warning for author review.
After every display block, immediately provide four columns whose `zh-CN` headers are `符号`, `数学定义或角色`, `取值范围 / 单位`, and `实际含义 / 物理解释（如适用）`; other languages use their catalog equivalents.
Do not add a serial-number column or invent domains, units, or physical meanings. State when something is not applicable. A global table never replaces a local table.

## File generation and navigation
Generate one `<ID>.md` per node and one `<edge-ID>.md` per EDGE_DETAIL edge. STRUCTURAL_ONLY has no independent file.
A regular card contains: independent two-column header (ID left/type right) → title → core formula → one-sentence role → details/incoming/outgoing navigation.
COMBINE is a 180×180 circle showing only ID, COMBINE, and the selected language's short merge/details terms. CASE uses the same color and circular style, with a diameter large enough for its ID and outgoing branch ports; its note carries the partition explanation rather than a continuous main chain. TRANSFORM is a 240×180 downward triangle showing ID, TRANSFORM, an operation title of at most six full-width units, and selected-language details. It remains a readable rectangle when the snippet is disabled. LOCAL_INTRODUCTION is an ordinary rectangular mathematical card.
The localized `zh-CN` headings `传入关系` (incoming relations) and `传出关系` (outgoing relations), or their selected-language equivalents, list every relation in a node note. Explanatory edges are reachable from both ends; structural edges link adjacent nodes or COMBINE.
Each relationship gives the adjacent node's content, relevant formula, and dependency use in place. When the adjacent node is COMBINE, expand all its direct inputs, combination purpose, current contribution, and output handoff by one level only; never copy its full derivation.
Every node note has `[[mindmap/<slug>.canvas#<ID>|定位原节点]]` for the `zh-CN` “locate original node” alias, or its selected-language equivalent, plus a full-map fallback.
Native Canvas does not guarantee node-fragment location or backlinks from text cards; never claim fully native bidirectional indexing.
Edge labels are plain text and cannot use wikilinks. Independent click-to-open edge explanations are not implemented; use the relationship directories in both endpoint notes.

## Information architecture and status
The graph header contains only the name, assumptions, and statement/basic definitions, plus an overview link and mathematical status. Do not crowd a card with long background prose.
The six context modules appear only in `index.md`. Repeated theorem basics in the graph and overview come from the same model.
`proved` means proved by the current argument, not visually reviewed.
For `refuted`, `theorem.counterexample` states an explicit counterexample and TARGET states the conclusion that negates the original proposition; the graph must not pretend that the original proposition holds.
`needs_assumption` records `missing_assumptions` and `open_obligations`; `partial` records `open_obligations`.
An incomplete model cannot use ESTABLISHES_TARGET. Established branches may retain open obligations, but graph validity never substitutes for an unfinished argument.
Create a separate entity for a corrected proposition and explain its relation to the original question in the overview. Proof by contradiction (CONTRADICTION) is not a counterexample (`refuted`).

## Local assumptions and explanatory layer
`scopes` contains `{id,title,kind:"local"|"induction",parent_scope?,opened_by,opening_edge?,closed_by}`; a node's `scope` references its innermost scope. Parent links form a tree. Groups contain all descendant-scope members and remain visual containers rather than inference edges. Case branches are inferred from paired CASE/COMBINE paths and receive no separate Canvas group.
`LOCAL_INTRODUCTION` has one genuine value-source input and one structural `OPENS_SCOPE` output. It sits in the parent scope; the output enters its child scope. A scope opened by `HYPOTHESIS_LOCAL` starts at a strict root with no incoming edge, including when its `parent_scope` is set. Such a nested root may use variables introduced by an ancestor scope opener; its descendants inherit those variables through proof paths from the root. A variable constructed later inside the parent scope does not enter that root's context. A local hypothesis following an introduction remains in the same scope.
`DISCHARGES` names one scope, a rule, generalized binding IDs, and discharged hypothesis IDs. Universal generalization closes an arbitrary-introduction scope, generalizes its bound variables, and discharges no hypotheses. Reductio, negation introduction, and conditional proof discharge hypotheses without generalizing variables. A proof using both operations closes the hypothesis scope first and the arbitrary-introduction scope second. Induction generalization retains its dedicated rule; a witness scope closes through existential elimination without generalization, and fixed data cannot be generalized. A paired case COMBINE records closures for its branch scopes. No scope result may flow outside before the declared closing edge or COMBINE.
Every strict mathematical node and every EDGE_DETAIL edge declares `uses_symbols` for free local bindings. Bound symbols have stable IDs and are cross-referenced by formula symbol tables. The validator checks declared visibility and dependency order; authors review whether the TeX actually matches those declarations. Scope and case structural checks do not establish exhaustive cases, witness validity, or the mathematical truth of generalization.
Place INTUITION or `strict:false` nodes in the localized non-proof group; the `zh-CN` title is `非证明说明`. They cannot feed a strict conclusion.

## Escaping and editing
Raw LaTeX fields have no delimiters; JSON serialization handles backslashes, so never escape them twice manually.
Use `\lvert`, `\rvert`, `\lVert`, `\rVert`, and `\mid` for absolute-value, norm, and conditional bars; then apply Markdown-layer table escaping.
Do not blindly replace every `|` with one mathematical command. The author must confirm display semantics.
Use UTF-8 without BOM and LF. The personal-notes heading is localized, but content exists only inside stable `personal:start/end` boundaries and is preserved verbatim across language rebuilds.
Edits to generated regions cause conflicts. Put mathematical changes into the model before rebuilding. Import layout changes with `import-layout`.

## Reading and continuous-main-chain contract (required for build and release)

`proof_flow`, node `navigation`, and operation-node input-usage records are required formal model content. Missing fields fail validation.

- `proof_flow`: `[{id,title,summary,nodes:[node IDs]}]`. Stages cover every node exactly once and have unique IDs and titles. `title` is a short natural-language link anchor with no formula; mathematical detail belongs in Markdown-capable `summary`. The mathematical author supplies stage meaning; topological rank is not a substitute. The overview renders stages and their node links.
- Each node's `navigation`: `{stage,role,motivation}`; `stage` references a stage ID. Predecessors, successors, scope, and start/target/non-proof identity are derived from the graph. EDGE_DETAIL note navigation reuses existing global roles and endpoint content.
- A pure-text condition or proposition may use a prose block with a stable ID as `reading_ref`. Without a core formula, `core` falls back to the first body prose block; complex nodes should select a reference explicitly. A text input's usage step must match the source verbatim, use start or condition, display the original proposition directly, and explain its verification role without inventing a formula or symbol table.
- Body blocks may have stable IDs. A node's `reading_ref` selects the formula or text proposition used in neighbor review and defaults to `core`. With a core formula, `core` is the node's core formula (the output for COMBINE) and a body/derivation formula block with identical content must supply its local symbol table. Other references point only to one uniquely identified block in that node's `sections`, never to a neighbor's neighbor.
- COMBINE `input_review`: `[{node,formula_ref,contribution}]`, exactly once per direct input. Title, formula, and symbol table come from the source node; the author supplies only the contribution here.
- COMBINE `input_usage`: `[{node,formula_ref,step_id,mode}]`, exactly once per input, with mode start/basis/condition. `start_input` agrees with the unique start record. A formula start is the first formula; no derivation formula may precede a text start. Every record binds a distinct real step ID. Its formula `latex/symbols` or prose `text` must equal the referenced source, or the stale copy is rejected. Basis/condition records bind main-chain apply rows that render a long downward arrow and right-hand box; start binds the first expression row. A result block cannot be an input-usage step. Mathematical review still verifies condition application and subsequent operations.
- COMBINE uses `combine_motivation/combine_method`; TRANSFORM uses `transform_motivation/transform_method`, and `transform_input` equals its sole strict predecessor. Both share `input_review`, `input_usage`, `derivation_chain`, and `output_handoff`.
- Other permitted structural relations are stored by the receiver in `input_context` as `{edge_id,contribution}`, covering each non-COMBINE structural input exactly once. Explanatory edges continue to use `detail` as their sole source; structural edges have no `detail`.

COMBINE order follows the selected-language equivalents of these exact `zh-CN` reserved headings: `导航`, `输入回顾`, `合并动机与意义`, `合并思路与工具`, `详细推导`, `合并结果`, `适用条件与核验`, `传入关系`, `传出关系`, `个人补充`. The final derivation formula equals `combine_output_latex` and the successor core formula. The main chain retains that final row, while the combined-result section intentionally repeats it as a summary with a local symbol table. Put any abbreviation expansion before the final main-chain row.

Table formulas use only short, single-line inline mathematics. The current threshold is 100 TeX characters; a formula containing a newline, line-break command, environment, or box moves to a display block directly below the table and is targeted by a link from the table. Every display block receives a four-column local symbol table. Escape a link-alias separator inside a table; parsing decodes only that separator and never accepts arbitrary path backslashes. Authors use semantic commands for mathematical bars; Markdown escaping must not change mathematical meaning.

The exact `zh-CN` generated headings `导航`, `输入回顾`, `合并动机与意义`, `合并思路与工具`, `详细推导`, `合并结果`, `适用条件与核验`, `传入关系`, `传出关系`, and `个人补充`, together with the exact prefix `输入公式 `, are reserved localized names. Their selected-language equivalents are also reserved. Authored sections cannot reuse them, and custom body headings cannot duplicate one another.

### Continuous-main-chain data interface

`derivation` stores formula/prose blocks, each with a unique ID. `derivation_chain` contains `rows` and `symbols`, and may contain `explanations` and `auxiliaries`. COMBINE/TRANSFORM cannot build or release without a continuous chain; `validate-model` also checks an existing chain.

- Expression row: `{kind:"expression",step_id,split_at,continuation?}`. `step_id` references an authored body expression. `split_at` is the start offset of a top-level relation in the TeX string; 0 anchors the complete proposition. It must not cut into a command or environment. `continuation` may omit the left-hand side only when it is unchanged; the generator never derives an expression.
- Apply row: `{kind:"apply",step_id,next_step,name,source? or auxiliary_ref? or external:true}`. Both neighbors must be expression rows, and `next_step` equals the immediately following expression ID. `name` is the justification name in the box.
- `source`: `{node,formula_ref}`, referencing content delivered by a current direct input only. The corresponding formula/proposition and symbol table must match the source. `input_usage` binds its first use to the same apply row; repeated use of other verified content from that input may have another apply row.
- `auxiliary_ref` references an auxiliary calculation ID in this node, and the justification block must equal its result block. `external:true` denotes an explicitly authored external mathematical rule whose name and applicability require review; it cannot replace a required input reference.
- `auxiliaries`: `[{id,steps:[block IDs],result_ref:block ID}]`. Every step references a formula block and the result is the final block. Render all steps inside the unique `auxiliary_ref` right-hand box, not in a separate display block. Every auxiliary result returns to explicit use in the main chain; promote it to a formal result node when reuse is needed.
- `explanations`: IDs of prose explanations after the chain. Every derivation block belongs to the main chain, an auxiliary calculation, or an explanation; none may be silently omitted.
- `symbols`: the sole four-column local symbol table covering every main expression, ordinary justification block, and auxiliary-calculation step. Input-block symbol tables validate coverage but are not inserted individually into the rendered chain.

Compile the entire main chain as one aligned display block. Long arrows share an anchor with the main relation. A `vphantom` placeholder with minimum height 3 em adapts to the right-hand box. Leave 2.5 em before and after arrows and 0.8 em between ordinary expressions. Put short box names to the right and multiline box names left-aligned on the next line inside the box. Never miscount the hidden placeholder copy as a second visible box.

Escape pure-text conditions as ordinary text while preserving inline mathematics, then embed them in the same main chain; never emit a bare Markdown paragraph that breaks the chain. Arrows support equality, inequality, and logical reasoning uniformly and mean application of a justification, not equality or equivalence.
