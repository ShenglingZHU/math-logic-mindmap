# Maintenance and Recovery

This page preserves the operational details that used to live in the main README. Start with the [English guide](../README.md), [French guide](README.fr.md), or [Chinese guide](README.zh-CN.md) for the normal workflow. The project root is the Obsidian vault. Run commands below from that root, or pass `--root <vault-path>` before the command when running elsewhere.

## Upgrading

Upgrade in the existing vault so its location and personal content remain intact. Read the new Release's migration notes, stop generation tasks, and close Obsidian before replacing files.

### Back up the complete vault

Copy the whole old project directory, including hidden directories, to a location outside the vault. Check that the copy includes `proof/`, `mindmap/`, `note/`, attachments and other personal files, `math-logic-mindmap.config.json`, `.obsidian/`, and `.build/backups/`. The formal models cannot be reconstructed from Canvas or notes. Neither `export-preview` nor the single retained backup of a topic is a complete upgrade backup.

### Replace system content, preserve personal content

Extract the new repository source archive into a separate temporary directory. Update only the following paths in the original vault; do not overlay or mirror the entire new archive onto it. For a whole-directory replacement, move the old directory outside the vault or remove it after verifying the backup, then copy in the new directory. Merging directory contents would leave obsolete modules or tests behind. Limit replacement to the exact paths below, not their parent directories.

| Action | Paths and boundaries |
| --- | --- |
| Replace whole system directories | `skills/math-logic-mindmap/`, `plugins/proof-routing/`, `tests/`, `docs/`. Preserve any personal additions separately from the backup; do not copy old modules or tests back into the new directories. |
| Replace supplied root files | `README.md`, `AGENTS.md`, `CLAUDE.md`, `pyproject.toml`, `setup.cfg`, `uv.lock`, `LICENSE`, `THIRD_PARTY_NOTICES.md`, `.editorconfig`, `.gitignore`, `.gitattributes`. A Release must identify any renamed or removed root files and the action needed. |
| Replace the project CSS | `.obsidian/snippets/math-logic-mindmap.css`. Save local changes first, then move personal styles into a separate snippet and enable it in Obsidian. Do not restore the entire old project stylesheet over the new one. |
| Update through the tools below | `.agents/skills/math-logic-mindmap/SKILL.md`, `.claude/skills/math-logic-mindmap/SKILL.md`, and the managed files in `.obsidian/plugins/proof-routing/`. Do not replace the parent `.agents/`, `.claude/`, or `.obsidian/` directories. |
| Keep all personal content | `proof/`, `mindmap/`, `note/`, attachments, other personal files, `math-logic-mindmap.config.json`, and existing `.build/` recovery material. Keep the bundled topics too: a user may have edited them. Do not import the new archive's examples over existing topics. |
| Keep personal Obsidian settings | All other `.obsidian/` content, including themes, workspace state, plugin and CSS enablement lists, other plugins, and their settings. |

Changes made to system files are not merged automatically: save them before upgrading and reapply them as needed afterward. Keep Advanced Canvas's existing `.obsidian/plugins/advanced-canvas/data.json`; merge only specific project settings required by the Release. Do not replace personal settings with the repository's five-key defaults or change the Advanced Canvas version as an incidental part of this upgrade.

### Reinstall, synchronize, and check

Use the existing virtual environment to reinstall from the original project root:

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe -m pip install -e .
```

```sh
# macOS / Linux
./.venv/bin/python -m pip install -e .
```

Recreate the environment only if it is unusable or the new release requires a different Python version. In the commands below, `python` means that same virtual-environment executable; replace it with the platform-specific path above if the environment is not activated.

```sh
python skills/math-logic-mindmap/scripts/canvas_tool.py sync-skills
python skills/math-logic-mindmap/scripts/canvas_tool.py check-skill-sync
python skills/math-logic-mindmap/scripts/canvas_tool.py sync-proof-routing
```

Read the Proof Routing preview before explicitly confirming the installation update:

```sh
python skills/math-logic-mindmap/scripts/canvas_tool.py sync-proof-routing --confirm proof-routing
python skills/math-logic-mindmap/scripts/canvas_tool.py check-proof-routing-sync
python skills/math-logic-mindmap/scripts/canvas_tool.py --version
python skills/math-logic-mindmap/scripts/canvas_tool.py --help
```

For the recommended Proof Routing setup, synchronization is required whenever its source changes: a partial or divergent installation copy blocks `release`. Keep using the source/preview/confirmation workflow rather than copying both versions manually. An intentionally fully absent installation copy still permits the existing fallback; its sync check does not pass and that is not the recommended setup.

Reopen the original vault and check an existing map and its node notes. Ordinary upgrades do not require the full regression suite. The repository's exact-settings test checks the minimal configuration shipped to users, not an actively used personal vault. If Obsidian has expanded `data.json`, extra defaults alone are not an upgrade failure, provided the five project-required values still match. Inspect failures rather than assuming all settings differences are harmless; see [Obsidian setup](obsidian-setup.md).

### Understand stale states and recover if needed

The presentation identity includes the tool package's Python files, schemas, tool version, project CSS, and the tracked Proof Routing installation files. When these change, previously published topics bound to the old identity report `STALE` for their machine and visual states. Documentation-only changes do not cause this. `STALE` means the old verification record no longer matches the current system; it does not mean published files are damaged, and existing maps remain readable.

There is no mandatory bulk rebuild during an upgrade. When you want a topic regenerated or its machine checks bound to the new system, validate its model, build, and release it using the workflow below. Import manual layout changes before rebuilding. Rebuilding does not restore an earlier visual-review conclusion; visual review remains optional and `UNREVIEWED` does not block release. Never edit manifest hashes to clear a state.

If an upgrade fails, stop writes and restore the complete pre-upgrade backup and its matching Python environment. Do not combine old and new system files.

Each future Release should briefly state whether migration is needed, the required actions, and whether plugins or topics need updating or rebuilding. If no migration is needed, say so explicitly.

### Historical migration: project rename

If upgrading an earlier installation after the project rename, reinstall the editable package, change external scripts to the `math-logic-mindmap` command, and rename any personal root configuration to `math-logic-mindmap.config.json`. The previous command and configuration name are no longer supported. The Python import name is `math_logic_mindmap`.

In an upgraded Obsidian vault, enable the `math-logic-mindmap` CSS snippet under Appearance; the previous snippet name no longer enables the circle and triangle styles. The two bundled examples were rebuilt and released during the rename. Their single retained backups contain the pre-rename manifests with old system paths. Restoring one will show `STALE`; rebuild and release it with the new tool rather than editing manifest hashes.

## Python and command entry points

Use Python 3.11 or newer and the virtual-environment setup in the README. On Windows, if `python` resolves to an unusable Microsoft Store alias, use `py -3.11` or the real Python executable instead. Installation supplies `jsonschema>=4.18,<5` and exposes the `math-logic-mindmap` command inside the environment. As an alternative without installing the project, run `python -m pip install "jsonschema>=4.18,<5"` and use the script directly. In all examples below, `python` means your chosen environment's interpreter; without activation, use `.\.venv\Scripts\python.exe` on Windows or `./.venv/bin/python` on macOS/Linux. The examples use the direct script path.

Each new topic stores its formal model at `proof/<slug>/<slug>.proof.json`, with its layout, checklist, and optional review files under the same `proof/<slug>/` directory. The model is the only formal mathematical source; generated Canvas and notes cannot reconstruct it.

```sh
python skills/math-logic-mindmap/scripts/canvas_tool.py validate-model proof/<slug>/<slug>.proof.json
python skills/math-logic-mindmap/scripts/canvas_tool.py build proof/<slug>/<slug>.proof.json
python skills/math-logic-mindmap/scripts/canvas_tool.py validate-bundle proof/<slug>/<slug>.proof.json --bundle .build/staging/<slug>
python skills/math-logic-mindmap/scripts/canvas_tool.py release <slug>
python skills/math-logic-mindmap/scripts/canvas_tool.py status <slug>
```

`build` writes only to `.build` staging and saves the normalized `render-config.json` for that build. `release` writes the Canvas to `mindmap/`, notes to `note/`, and backs up changed published content. Mathematical conclusion, machine, runtime, and visual states are tracked separately. The default visual state is `UNREVIEWED`; it does not block release or certify the mathematics.

## Language, colors, and presentation identity

`math-logic-mindmap.config.json` controls the language and six node-role colors of the next build. Without the file, Chinese and the original palette are used. Supported normalized languages are `zh-CN`, `en`, and `fr`; common aliases such as `zh`, `en-US`, and `fr-FR` are accepted. Colors are six-digit hex values; omitted roles use defaults. A new or translated model must set `presentation.language` to the normalized language. Older models without that field are treated as Chinese. A mismatch between model and build language stops `build`.

For an older topic whose language differs from the current global setting, `build proof/<slug>/<slug>.proof.json --language zh-CN` overrides only that build's language. Colors still come from the root configuration. The tool does not translate mathematical prose. Language and colors are frozen into staging configuration, Canvas metadata, and the release manifest. Editing global settings does not alter existing maps or make their states stale; rebuild and release a topic to apply new settings. Scope groups, non-proof groups, and edge colors are outside the six-color palette. Role colors are Canvas accents, not necessarily the final card backgrounds in every theme. The original palette preserves the existing light and dark styles; custom colors are used to derive role backgrounds.

The readable Proof Routing source is `plugins/proof-routing/`; `.obsidian/plugins/proof-routing/` is its installation copy. Before publishing with that plugin, preview synchronization, explicitly confirm it, and check the copy:

```sh
python skills/math-logic-mindmap/scripts/canvas_tool.py sync-proof-routing
python skills/math-logic-mindmap/scripts/canvas_tool.py sync-proof-routing --confirm proof-routing
python skills/math-logic-mindmap/scripts/canvas_tool.py check-proof-routing-sync
```

Then build and release the topic being regenerated. A fully absent installation copy permits deliberate fallback; a partial or divergent copy blocks release. Proof Routing displays downward orthogonal lines and crossing bridges; without it, Advanced Canvas uses `square` routing. Changes to its tracked installation files change presentation identity, so topics bound to the previous identity report `STALE`. Rebuild and release a topic to refresh its machine state when needed; visual review is separate and optional. See [Upgrading](#upgrading) and [Obsidian setup](obsidian-setup.md).

## Layout and personal edits

Layout favors a main line, nearby conditions, and local scopes. Same-column edges are vertical; cross-column edges follow a downward–horizontal–downward route. Ordinary clear crossings are allowed, with Proof Routing drawing bridges. Routes through unrelated cards or long collinear overlaps block release. `build ... --layout-report` places `layout-report.json` and `layout.svg` in hidden staging; the SVG is a schematic, not an Obsidian rendering.

After dragging or resizing cards in Obsidian, import the layout before rebuilding:

```sh
python skills/math-logic-mindmap/scripts/canvas_tool.py import-layout <slug>
python skills/math-logic-mindmap/scripts/canvas_tool.py build proof/<slug>/<slug>.proof.json
python skills/math-logic-mindmap/scripts/canvas_tool.py release <slug>
```

Import accepts node/group positions, sizes, and unmanaged extra fields. It does not accept changed text, added nodes, or changed logical links; ports and routes are recalculated. The personal-additions region of node notes survives regeneration, while edits to other generated regions are reported as conflicts. `build ... --relayout` deliberately ignores imported layout overrides. If new nodes conflict with fixed manual positions, repair the layout rather than overwriting those positions.

## Review and preview

```sh
python skills/math-logic-mindmap/scripts/canvas_tool.py review-template <slug> proof/<slug>/<slug>.visual-review.json
python skills/math-logic-mindmap/scripts/canvas_tool.py record-review <slug> proof/<slug>/<slug>.visual-review.json
python skills/math-logic-mindmap/scripts/canvas_tool.py status <slug>
```

The reader checklist is `note/<slug>/_review-checklist.md`; final states and file hashes are in `proof/<slug>/<slug>.manifest.json`. Visual review is optional and starts as `UNREVIEWED`. After finding an issue, revise, rebuild, and release again. `export-preview <slug> <new-directory-outside-the-vault>` exports a separate draft vault without creating duplicate draft notes in the main vault. This export contains readable artifacts, not a full backup of the formal model.

## Deletion, backups, and interrupted release

Close the topic's Canvas and note tabs in Obsidian before removal. The first call only previews the active content, caches, reviews, personal additions, unmanaged attachments, modified managed files, and backups to be removed:

```sh
python skills/math-logic-mindmap/scripts/canvas_tool.py remove-topic <slug>
python skills/math-logic-mindmap/scripts/canvas_tool.py remove-topic <slug> --confirm <slug>
```

Confirmation removes the topic's `proof/`, `mindmap/`, `note/`, staging, failed builds, and in-project release backups, but leaves shared system files and previews outside the vault alone. Copy the complete topic source and artifacts outside the vault first if future restoration matters. The same slug may be reused after removal, but the mathematical argument and Skill Stages A–D must be completed again. If Advanced Canvas recreates an open deleted Canvas, close its tabs and repeat the preview and confirmed cleanup before rebuilding.

The tools work without Git and do not manage version history. `.build/backups/<slug>/` retains only the preceding version before the most recent real published-content change. Repeated releases do not replace that backup; metadata-only releases for reports, reviews, or presentation identity do not create a content backup. On a first release, or when no earlier content exists, `retained_backup` can be empty.

If release is interrupted, stop generation, restore `mindmap/`, `note/`, and the manifest for that slug from its single retained backup, then run `validate-bundle` and `status`. Do not edit hashes manually.

## Project regression checks

These checks are for system maintenance and release validation, not a required end-user upgrade step. Run the exact public-configuration checks in a clean distribution copy before opening it in Obsidian. Test personal-vault behavior in a separate copy; do not reset personal settings just to satisfy the published-defaults test. Before publication, a distribution copy must respect the intended file list and `.gitignore` exceptions; after publication, verify the actual downloaded source archive as well. Do not include local environments, build caches, private Obsidian state, or the external Advanced Canvas program in that copy.

```sh
python -B -m unittest discover -s tests -v
math-logic-mindmap check-skill-sync
math-logic-mindmap sync-skills
math-logic-mindmap check-proof-routing-sync
```

When releasing plugin changes, set `MATH_LOGIC_MINDMAP_REQUIRE_NODE=1` for the regression run: missing Node must fail the plugin geometry tests instead of silently skipping them. After changing Skill entry points, run `sync-skills` and `check-skill-sync`. After changing Proof Routing, use the preview/confirm/check sequence above. Routine topic generation should follow the [project Skill](../skills/math-logic-mindmap/SKILL.md) rather than reading tests or unrelated proof topics.

The [Tests workflow](../.github/workflows/tests.yml) runs the full regression suite and both synchronization checks on Windows, Ubuntu, and macOS with Python 3.11 and Node 24. Python 3.11 covers the minimum supported version; Node 24 provides an LTS runtime for the plugin geometry core, not Obsidian/Electron compatibility validation. Local Python 3.12 results are supplementary and do not add another CI matrix entry. The workflow runs for default-branch pushes, pull requests, and manual dispatches; other branch pushes produce a skipped job. New PR runs cancel older runs for the same PR. Default-branch pushes and manual dispatches use separate concurrency groups for each run, so subsequent runs do not replace them; different PRs and event types do not cancel one another. This policy does not prevent manual cancellation, platform failures, or timeouts. CI requires Node for the plugin geometry tests and checks synchronization without repairing files. It installs only the runtime dependencies declared in `pyproject.toml`, not the project itself; `uv.lock` is not used, so compatible dependency updates can change the resolved versions.

CI sets `PYTHONIOENCODING=utf-8` for standard streams and runs the parent regression process with `python -X utf8=0 -B -m unittest discover -s tests -v` to retain the system's default file encoding. This does not make a hosted Windows runner use cp936. The existing isolated-copy child process still enables UTF-8 mode and skips only its recursive copy test. Ordinary regressions use fixtures and temporary vaults; this workflow does not check published examples, mathematical correctness, or actual Obsidian/Electron rendering.

Before a release, use `git archive` to extract the candidate commit into a fresh temporary directory. In that copy, use an independent Python 3.11 environment and Node 24, install the declared runtime dependencies, and run the same checks and environment settings as the workflow. Confirm that the copy includes the generated Skill entry points and the Obsidian files allowed by `.gitignore`; do not generate missing files before checking. Before publishing the release, confirm that the candidate commit has passed all three platforms in GitHub Actions, and retain its identifier and the successful run URL. CI checkout verifies that committed content is sufficient for the tests; it does not replace the pre-publication file-list review for accidentally included private files.
