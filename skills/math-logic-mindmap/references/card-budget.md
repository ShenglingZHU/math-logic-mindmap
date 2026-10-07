# Card Content Budgets and Size Estimation

Budgets are Canvas-specific hard rules that replace browser measurement during builds; they do not guarantee that real MathJax never overflows.
A regular card title is limited to 18 full-width character units, with Latin characters counting as 0.5 unit; the role summary is limited to 36 such units.
Allow at most one core display formula and at most 240 raw TeX characters. Complete structured logical formulas may use more than two lines when the estimated card height remains at most 480 px. Complex derivations and large tables belong only in notes.
A title is one paragraph and one line, with no manual line breaks. When it exceeds the budget, write a mathematically equivalent shorter summary rather than truncating or omitting proof content.

Regular cards use static widths of 400/480/560/640/720/800 px, height ≥ 280, and a budget ceiling of 480 px; body text is 16 px, titles are 18 px, line height is 1.6, and padding is 20 px.
Estimate body lines from the selected inner width. Estimate formula width conservatively from supported common TeX atoms, spacing, fractions, and scripts with a 10% margin. Estimate height at 38 px per line, adding space for fractions, sums, and scripts.
Add the header, title, role, formula, navigation, and margins, multiply by 1.25, and round upward to a multiple of 8 px.
COMBINE uses a 180×180 circular template showing only a short ID, COMBINE, and the selected language's short merge/details words; the ID is at most six ASCII characters. TRANSFORM uses a 240×180 downward-triangle interaction container; its title is at most six full-width character units with no line break, and its safe content area uses approximately 20 px / 58 px / 70 px top-side-bottom padding. Built-in Chinese, English, and French fixed strings must fit the same templates. Formulas and complete explanations belong only in notes.
COMBINE remains 180×180. Distinguish multiple inputs with small top-port offsets and, once routes are safe, place them near and around the COMBINE. Do not enlarge the node or create routing-capacity nodes because of the input count.
Unknown commands, complex environments, and possible excessive width produce explicit risks, never a claimed measurement PASS. Inspect genuinely narrow or long formulas in Obsidian first.

Users may enlarge cards; `import-layout` rejects dimensions below the estimated minimum. Circles must retain equal width and height.
Port offsets for downward orthogonal routing do not change content-size budgets; `import-layout` still must not shrink a card below its estimated minimum.
If a single-line estimate exceeds 800 px, retain 800 px and report a risk. When a natural break exists, suggest a shorter line; never rewrite the formula automatically. Reject an estimated regular-card height above 480. A user may enlarge an already generated card when genuinely necessary, but must not solve the problem by shrinking the font or clipping content.

`card_formula_display` defaults to `full`. Set it to `summary` only when the complete core formula exceeds the card budget; the card then uses its existing title, role summary, and details link while the node note retains the complete formula. This field does not contain a second mathematical statement.
Advanced Canvas `dynamicHeight` defaults to false. After temporarily enabling automatic height as a repair tool, import the dimensions and inspect downstream layout.
A graph may be released after JSON checks pass; if real Obsidian reveals a header, MathJax, link, or theme issue, continue adjusting it.
