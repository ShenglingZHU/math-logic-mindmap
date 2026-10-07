# Continuous Main-Chain Derivation Layout Contract

This project follows the style supplied by the user: one core input develops along a vertical main chain, while other inputs enter in sequence through right-hand justification boxes beside long downward arrows. This user requirement takes precedence over the earlier format-math-derivations restriction that limited arrows to equality chains.

## Logical proposition typography

For a displayed implication, put its premise and consequent on separate lines and indent the consequent one `\quad` farther than the premise, including the `\Rightarrow` marker. For an existential assertion, put the binder and “such that” on separate lines and indent the latter one further level. If an explicit `\forall` is present, put it on the outer line, the premise one level below, and the consequent another level below; do not introduce a previously implicit quantifier merely for layout. Put two or more simultaneous peer conditions under a single left brace, one left-aligned proposition per row, not relation-aligned equations. The brace in this template means all listed conditions hold; write `\lor` and explicit grouping for alternatives. Localize words inside `\text{}` to `presentation.language`. A short conventional domain list such as `a,b\in\mathbb{Z}` may remain one row when it improves card fit.

Use one complete inner `aligned` environment for the proposition and `\left\{\begin{aligned}...\end{aligned}\right.` for a condition list; do not place a bare top-level `\\` or `&` into a main-chain expression. For example:

```latex
\begin{aligned}
&x\in\mathbb{Q}\\
&\quad\Rightarrow\quad\exists m,n\in\mathbb{Z}\\
&\qquad\text{such that}\quad\left\{\begin{aligned}
&n>0\\
&\gcd(m,n)=1\\
&x=m/n
\end{aligned}\right.
\end{aligned}
```

For a theorem with an existing explicit universal quantifier, use the same hierarchy:

```latex
\begin{aligned}
&\forall z\in\mathbb{Z},\\
&\quad 2\mid z^2\\
&\qquad\Rightarrow 2\mid z
\end{aligned}
```

When the complete proposition enters a continuous main chain, its expression row uses `split_at: 0` so the outer alignment never cuts the inner environment. `\Rightarrow` inside the proposition asserts implication; a long downward chain arrow means an applied justification. Keep multiline propositions in formula blocks, not inline prose mathematics.

## 1. Scope and meaning of arrows

Use this structure uniformly for equalities, inequalities, and logical reasoning. A long downward arrow means “apply the justification on the right to reach the next step”; it does not state that the expressions above and below are equal or equivalent. Every row retains its real equality, inequality, implication, or complete proposition. Never change a mathematical relation for layout.

Add an arrow only when a genuine justification enters. Do not decorate headings, definition lists, case labels, or unrelated paragraphs with arrows. Continue simple internal algebra directly on the next line.

## 2. One main chain, one display block

Choose the actual formula or proposition of one input node as the start. Use one aligned display block for the main chain from top to bottom through the final combined result. Align neighboring main expressions at the same relation position; omit a repeated left-hand side only when it has not changed.

Every introduced justification appears in this order: expression before transformation → long downward arrow and concrete right-hand justification box in the same display block → expression after application.

Do not output input boxes as separate display blocks joined by prose. Do not insert paragraphs, node-link directories, or symbol tables into the main chain. Put reference links in the input review and justification names inside the boxes.

## 3. Justification boxes and long arrows

Left-align box content, with the formula as the primary content and the name as a compact annotation. Put a short formula's name to its right; put the name of a multiline or long formula on the next line inside the box to avoid unnecessary width.
For a basis from an input node, the generator appends the source ID automatically inside the topic parentheses, for example `(induction points lie in the interval, H3)`. The authored `name` contains only the topic, never a handwritten ID. Independent external theorems and auxiliary calculations do not receive input-node IDs.

Align the arrow with the relation in the main chain and place it to the left of the box. Use a genuine long single downward arrow whose hidden equal-height placeholder adapts to the entire box; never substitute a short inline arrow.

Standard compilation skeleton:

```latex
\begin{aligned}
F_0 &= F_1
\\[2.5em]
&\left.\vphantom{\boxed{\displaystyle B\qquad(\text{justification name})}}
\rule{0pt}{3em}\right\downarrow
\qquad\boxed{\displaystyle B\qquad(\text{justification name})}
\\[2.5em]
&=F_2
\\[0.8em]
&=F_3.
\end{aligned}
```

`F/B` indicate layout positions only; actual complete mathematical content must be substituted. Inequalities retain their real inequality signs and logical derivations retain complete propositions; do not force the example's equals sign onto them. Leave 2.5 em above and below an arrow-and-box row and 0.8 em between ordinary expression rows. A placeholder box is not a second visible box; do not count occurrences of `boxed` in TeX to infer the number of justifications.

## 4. Auditable binding between inputs and steps

COMBINE and TRANSFORM must provide `derivation_chain`; see `canvas-and-notes.md` for the data contract. Authored derivation blocks with IDs are content sources. Expression rows reference authored expressions; apply rows reference a justification and bind the immediately following expression. A local TRANSFORM applicability rule may appear in a right-hand box with `external:true`, but an independent proof branch must enter through COMBINE first.

The unique `start` is the first row. Every other input corresponds to an apply row at its actual point of use. A box's `source` references the formula or proposition of a current direct input and must match its content and symbol table; do not write only “N4 gives an upper bound.”

Each apply row introduces one important justification. If two important theorems are required, use two application steps with an intermediate result. Verify conditions and variable mappings before or after the chain; the presence of a box, arrow, and complete ID does not prove mathematical correctness.

## 5. Internal transformations and auxiliary calculations

Continue previously introduced definitions, substitutions of the same quantity, and elementary algebra directly. One-use mechanical work that does not deserve a visible TRANSFORM belongs in this local derivation or an ordinary explanatory edge's `detail.transition_steps`. When a visible TRANSFORM is warranted, keep its continuous mechanical stretch in one main chain; a reused intermediate result breaks that stretch. The first use of an important external justification must be visible through apply.

When an auxiliary calculation is genuinely required, place every authored formula step in a multiline right-hand justification box at the point where the main chain uses it. Its last step is the stable result reference, and the arrow is followed immediately by the main expression after application. Do not create another display block or symbol table for the auxiliary calculation, and do not let it depend on a later main-chain result. Promote an auxiliary conclusion needed in multiple places to a formal LEMMA/result node.

Do not move the real main derivation into an auxiliary calculation or insert unrelated work into the main chain. A construction or logical operation may change the object of the main expression; in that case display the complete new expression and never omit a changed left-hand side.

## 6. Symbols, explanations, and results

Place one four-column local symbol table after the main chain, covering every formula step in main expressions, ordinary justification boxes, and auxiliary boxes. Do not split the table by box. Preserve pure-text conditions as authored text, which may include inline mathematics; do not fabricate a mathematical conclusion.

Each symbol-table row explains exactly one notation item. Represent sequences with a generic subscripted notation. Never put multiple symbols in one row with top-level commas, semicolons, `\quad` / `\qquad`, or explicit TeX spacing. When a justification box reuses a source formula, its symbol rows and order must exactly match the source block. Deduplicate the main-chain table by first appearance and make it cover exactly every main expression, justification box, and auxiliary calculation.

Keep step explanations and condition checks outside the chain. The main chain must include the final result; do not remove its last expression for the localized section named by the `zh-CN` reserved heading `合并结果` (“combined result”), or its selected-language equivalent. That section intentionally repeats the final formula with its own symbol table and explanation as an independently readable summary; this repetition is allowed.

Do not box the final result by default; boxes are for justifications. The successor node explains the result and its use without repeating the complete main chain.

## 7. MathJax and acceptance

Model TeX contains no display delimiters. The generator emits Obsidian double-dollar display blocks and inline mathematics consistently. It injects no CDN and requires no new user plugin.

Regression coverage includes equality, inequality, logical reasoning, short justifications, multiline justifications, and complete auxiliary-calculation boxes. Check compilation, the visible long-arrow count, before/after step binding, relation alignment, box height and name, the sole symbol table after the chain, and final-result identity.

An isolated MathJax/browser layout check proves only that environment's result. Without a real Obsidian inspection, status remains `UNREVIEWED`, but release is not blocked. Continue repairing clipping, collisions, or errors when found.
