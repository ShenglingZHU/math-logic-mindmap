# Obsidian Setup and Review

1. Extract the complete project with its hidden directories. Before first opening the vault, download `main.js`, `manifest.json`, and `styles.css` from the [Advanced Canvas 7.0.0 official release](https://github.com/Developer-Mike/obsidian-advanced-canvas/releases/tag/7.0.0). Place them directly in `.obsidian/plugins/advanced-canvas/`, without an extra nested folder, and keep the supplied `data.json`. The external plugin's program files are not distributed with this repository.
2. Open the project root as a vault in desktop Obsidian. If a trust prompt appears, allow community plugins only if you trust their code; otherwise use Settings → Community plugins → Turn on community plugins. Keep the Canvas core plugin enabled. The repository does not publish `core-plugins.json`, so it does not replace personal core-plugin choices.
3. Confirm that **Advanced Canvas 7.0.0** and **Proof Routing 0.6.1** are enabled; the supplied community-plugin list already selects both. Proof Routing's readable source is `plugins/proof-routing/`; `.obsidian/plugins/proof-routing/` is a replaceable installation copy that displays deterministic downward orthogonal routes and “horizontal over vertical” crossing bridges.
4. Under Appearance → CSS snippets, confirm that `math-logic-mindmap` is enabled. Its file and enabled setting are supplied; refresh the list and enable it if necessary. Keep personal styles in a separate snippet so upgrades can replace the project's CSS.
5. Start with the default Obsidian theme and inspect both light and dark modes. Review again after a plugin or theme upgrade; do not reuse conclusions from the old environment.
6. Disable automatic creation of Canvas edges from file links; proof edges may only come from the model. Do not use a blurred-background focus mode as a substitute for the original mathematical-graph interaction.
7. Keep dynamic card height disabled by default. Plugin-based automatic height may be used to repair long content; afterward save, run `import-layout`, rebuild, and check for collisions.

If the vault was already open when you added the plugin files and Advanced Canvas does not appear, reload plugins or restart Obsidian, then check the installation path and enabled state. To reproduce the verified environment, keep Advanced Canvas 7.0.0: the community catalog or applying an update may install a newer, unreviewed version. Checking for updates alone does not install them. Review the display again if you choose to update.

The published Advanced Canvas `data.json` intentionally contains exactly five project-required settings:

| Key | Required value |
| --- | --- |
| `nodeStylingFeatureEnabled` | `true` |
| `edgesStylingFeatureEnabled` | `true` |
| `autoFileNodeEdgesFeatureEnabled` | `false` |
| `autoResizeNodeFeatureEnabled` | `false` |
| `autoResizeNodeEnabledByDefault` | `false` |

Advanced Canvas may expand this file with its complete defaults after settings are saved. The exact-configuration test is for the clean distribution copy, before opening it in Obsidian; do not publish expanded personal defaults or weaken the test. In a personal vault, preserve existing settings and check these five values. Extra defaults alone do not indicate upgrade failure, but changed required values need attention. Do not reset a user's full configuration just to pass the distribution test. The same distinction applies to personal appearance and community-plugin enablement lists. See [Upgrading](maintenance.md#upgrading).

### Proof Routing plugin file safety

Obsidian Community plugins execute with the application's local permissions. Review `plugins/proof-routing/` before leaving Restricted Mode and enabling the plugin. Proof Routing is desktop-only; mobile Obsidian ignores it. Uninstalling deletes only the installation copy. Restore it with `sync-proof-routing`, review the preview, then pass `--confirm proof-routing`. Without the plugin, Canvas falls back to the Advanced Canvas `square` route, but the presentation identity changes and existing visual reviews immediately become stale.

## Excluding development content
To reduce development noise, optionally add `skills/`, `plugins/`, `docs/`, `tests/`, and `proof/` under Settings → Files and links → Excluded files.
This reduces development-material noise in search and graph views; it does not make files invisible or guarantee exclusion from every index.
Do not rely on exclusions to isolate a nested draft vault. `.build/` is hidden staging, not a vault for direct preview.
Entry-point files may also be excluded to taste, but do not exclude `mindmap/` or `note/`.
The normal toolchain does not rewrite `.obsidian/app.json`; appearance and workspace files remain user-maintained.

## Support and boundaries
Files follow Advanced JSON Canvas 1.0-1.0 fields: circle, square/a-star, dynamicHeight, and styleAttributes.
The verified combination is Obsidian 1.13.7 on Windows desktop, Advanced Canvas 7.0.0, Proof Routing 0.6.1, and the default light/dark themes. The Proof Routing `minAppVersion` is only a load boundary, not a claim that every compatible Obsidian version was reviewed. Record the actual plugin and Obsidian versions in each review; any other combination is unreviewed until inspected.
Native mode can still open `.canvas` files and ordinary note links, but it does not guarantee circles, orthogonal lines, node-fragment location, or backlinks from text cards.
Node notes also provide a full-map fallback. Edge labels are plain text; open an edge note from the relationship lists at either endpoint.

## Inspection order
First open the current `mindmap/<slug>.canvas`. Check the header, the inverted-tree structure from multiple roots to one target, circular COMBINE cards, downward-triangle TRANSFORM cards, pale-green intermediate results, top-to-bottom flow, and scopes.
Temporarily disable the `math-logic-mindmap` snippet. Confirm that TRANSFORM degrades to a readable rectangle and that its details link remains clickable. Re-enable it, then inspect triangle borders, transparent corners, and link hit areas in light and dark themes and at several zoom levels.
Open every node detail and every explanatory edge from both endpoints. Try locating the original node and opening the full map.
Inspect the longest formula and every local symbol table. Source containing `$$`, MathJax commands, or library files is not rendering evidence.
Check Chinese text, `boxed`, and `Bigg downarrow`; absolute-value, norm, and conditional bars must not break tables.
Complete every item in `_review-checklist.md`, then bind the version with `review-template` / `record-review`.

## Handling geometry risks
Real port conflicts and COMPACTION entries in machine reports require visual inspection and must not be treated as automatically verified; ordinary multi-input and multi-output port loads are informational statistics only.
Keep the mathematical DAG unchanged first, and adjust the spine, branch order, first-use positions of roots, node spacing, and local scopes. `downward-orthogonal` uses vertical lines for nodes in one column and midpoint, two-bend orthogonal lines for nodes in different columns. Clear crossings are allowed; outer corridors are not. Keep every logical edge downward and traceable.
Small port offsets distinguish multiple inputs and outputs. Routes through cards and long collinear overlaps must be repaired; ordinary crossings do not block release. In real Obsidian, inspect horizontal crossing bridges, non-backtracking merged bridges at dense intersections, global label avoidance, and recomputation after dragging. `layout.svg` does not show plugin-derived bridges and cannot replace this visual check.
When structure is unchanged, `import-layout` preserves the manual layout and `build` rechecks card overlap and direction. Change the Proof Model first when content changes.

Sources: [Obsidian Canvas](https://help.obsidian.md/plugins/canvas), [Settings](https://help.obsidian.md/settings), [Advanced Canvas](https://github.com/Developer-Mike/obsidian-advanced-canvas), and the [format specification](https://github.com/Developer-Mike/obsidian-advanced-canvas/blob/main/assets/formats/advanced-json-canvas/spec/1.0-1.0.md).

## Before deleting a topic

Close that topic's Canvas and note tabs in Obsidian, and exit Obsidian if necessary, before running `remove-topic <slug>` for a preview. The tool does not rewrite `.obsidian/workspace.json` or recent-file records. If Advanced Canvas recreates a Canvas with the same name after deletion, close the relevant tabs, preview and confirm cleanup again, and only then rebuild.

`proof/<slug>/<slug>.proof.json` is the formal mathematical source. Confirmed deletion also removes the layout, manifest, mathematical review, visual review, generated notes, Canvas, and in-project build state for the topic. The system cannot reconstruct the Proof Model from Canvas or notes. To preserve the result for possible restoration, first copy the complete topic source and artifacts outside the vault. `export-preview` exports only readable Canvas and notes and is not a complete source backup. The same slug may be reused after deletion, but Stages A–D must be completed again.

The user must separately manage previews exported outside the vault.
