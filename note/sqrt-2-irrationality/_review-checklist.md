# sqrt-2-irrationality · Obsidian review

Visual status: **UNREVIEWED**

A bundle may be released after basic machine checks; this page records later visual feedback and is not a release gate.

- [ ] `reading_context` Navigation stages and one-level neighbouring combination inputs and outputs are readable; incoming, outgoing, and stage links work.
- [ ] `input_tables` Input-review columns and links work; long formulas appear below the table without clipping or horizontal scrolling.
- [ ] `derivation_bases` Every applied basis in the continuous derivation has a long down arrow and a right-hand box; source IDs and relation symbols are correct; one symbol table follows the chain.
- [ ] `chain_geometry` Long arrows align with relation symbols and accommodate multiline basis boxes; formulas, boxes, and names do not collide or clip.
- [ ] `mathjax` Mathematics, selected-language text, boxed, Bigg downarrow, and four-column tables render correctly with no raw TeX or errors.
- [ ] `containment` Regular cards, circular COMBINE cards, and triangular TRANSFORM cards show complete IDs, content, and detail links without clipping, scrolling, or overflow.
- [ ] `headers` Regular cards place ID left and type right; fixed COMBINE and TRANSFORM text and IDs are ordered correctly.
- [ ] `links` Node details and explanatory edges are reachable from both ends; node-location and full-map fallbacks work.
- [ ] `routing` Each edge travels downward without crossing unrelated cards; same-side arrows are traceable and do not imply false merging or shared trunks; horizontal bridges at ordinary orthogonal crossings are clear and unobscured by labels.
- [ ] `labels` Every explanatory edge has one label and structural edges have none; labels are attributable and cover no card or edge.
- [ ] `scopes` Nested local-scope groups and CASE/COMBINE pairs are correct; non-proof notes do not look like strict premises.
- [ ] `themes` Default light and dark themes remain readable; TRANSFORM and result colors and borders are correct; disabled snippets degrade readably; symbol tables do not scroll horizontally.
- [ ] `zoom` At 100%, 200%, and 400%, formulas and selected-language text are clear; pan and zoom preserve navigation.

## Routing convention

Nodes in one column use vertical edges; other edges go down, across, then down. Clear crossings are allowed; with Proof Routing enabled, horizontal segments bridge over vertical ones and dense crossings merge into one longer bridge, without adding distant corridors merely to remove crossings.

## Environment and record

Use review-template to create evidence bound to the current files, then record Obsidian, Advanced Canvas, theme, reviewer, and evidence for every check. Unobserved checks remain UNKNOWN.
