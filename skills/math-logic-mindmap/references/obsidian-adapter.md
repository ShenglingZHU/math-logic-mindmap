# Obsidian / Advanced Canvas Capability Contract

Target format: JSON Canvas 1.0 + Advanced JSON Canvas 1.0-1.0.
Authoritative interfaces: [JSON Canvas](https://jsoncanvas.org/spec/1.0/) and [Advanced JSON Canvas](https://github.com/Developer-Mike/obsidian-advanced-canvas/blob/main/assets/formats/advanced-json-canvas/spec/1.0-1.0.md).
Advanced Canvas is the generation target. Artifacts may be released after basic structural checks; real-environment inspection is later feedback and is not bound to release identity.

## Established fields
`metadata.version="1.0-1.0"`; every node and edge retains the required standard JSON Canvas fields.
`node.styleAttributes.shape="circle"`; regular nodes are rectangles; non-proof nodes use `border="dashed"`.
`node.dynamicHeight=false` by default; while repairing, a user may enable it temporarily and then import the resulting height.
`edge.styleAttributes.pathfindingMethod="square"` is the fallback when the plugin is unavailable. Active display uses `downward-orthogonal` to generate zero- or two-bend orthogonal routes, lets horizontal arcs bridge over vertical lines at ordinary crossings, merges dense intersections into long bridges, and globally keeps labels away from remaining visible bridges; `path="solid"`.
`canvas.metadata.proofRouting.profile="downward-orthogonal"`; `edge.proofRoute` stores generator-managed `fromOffset/toOffset/midOffset`, not derived bends.
`node.styleAttributes.proofRole` is a project-specific styling property used by CSS, not a standard property.
Preserve unknown plugin properties where possible during layout import; model-managed semantics, colors, and arrow fields take precedence.
Do not enable Auto File Node Edges: note references must not create proof dependencies automatically.

## Colors and text
The root `math-logic-mindmap.config.json` configures six colors for external results, COMBINE, TRANSFORM, intermediate `result:true`, TARGET, and givens. Defaults are respectively #B39DDB, #E5C85B, #D9DEE7, #CFE8CC, #E69A9A, and #88BBDD. TARGET takes precedence over result. INTUITION uses a transparent/default background and a gray dashed border. Configuration values are role colors/accent colors written to Canvas, not necessarily the final card background in a theme. The default palette preserves the exact original light/dark appearance; for custom colors, the snippet derives role backgrounds from the complete `--canvas-color` value while preserving theme text colors, so a small change near a default should not cause an abrupt style jump.
Explanatory edges use #4A90C4, a solid line, and one label. Structural edges use #888888, a solid line, and no label.
Color is not the sole semantic signal: every node displays its type, while the presence of a label and the corresponding note distinguish explanatory from structural edges. Similar or identical colors across roles are not rejected.
CSS adapts backgrounds and contrast for Obsidian's default `theme-light` and `theme-dark`; users need not change the global font.

## Native fallback
When Proof Routing is disabled, Advanced Canvas displays `square` routes. Cards and normal note links remain readable, but precise midpoint horizontal segments and crossing arcs may change or disappear.
Also provide a full-map link; never claim accurate native node-fragment location.
Plugin load state does not affect release. Visual status remains `UNREVIEWED` until someone performs a real inspection and reports it.

## Replacements for HTML interaction
HTML right panel → `ID.md`; clickable edge explanation → relationship directories in both endpoint notes; background modules → `index.md`.
Fit, reset, wheel, and dragging use Obsidian host behavior; do not force the original HTML's button positions or wheel convention.
Independent node/edge focus, clearing the background panel, hit width, and transparent hit paths are not implemented in the first version.
Do not use a plugin's blurred focus as a substitute for the original unblurred focus behavior.
Obsidian owns MathJax rendering; the generator does not inject the HTML MathJax runtime, CDN, or scripts.
Source files have no runtime network dependency. Plugin installation requires network access, but this document does not enable plugins for the user.
Do not generate images in place of mathematical nodes. Canvas-to-PDF printing is not promised; the original HTML printing mechanism is replaced and outside this release.

