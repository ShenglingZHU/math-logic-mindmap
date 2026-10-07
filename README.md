# Math Logic Mindmap

[English](README.md) · [Français](docs/README.fr.md) · [中文](docs/README.zh-CN.md)

**From what is known, understand why each step happens, and let logic flow to the conclusion.**

## 1. Project at a glance

Math Logic Mindmap is a project in which AI tools such as Codex and Claude Code **break down the logic** of a theorem proof or problem solution and create a **proof logic flow map**. Guided by the project rules, the assistant first works out and self-checks the mathematical argument, then identifies its dependencies and generates an Obsidian Canvas with linked Markdown notes. Obsidian with Advanced Canvas is the intended viewer.

## 2. Quick start

### ① Open an existing example

1. Download the [complete repository](https://github.com/ShenglingZHU/math-logic-mindmap) with **Code → Download ZIP**, or choose a Release's **Source code** archive for a published version. Extract it with its hidden directories. Git is not required; a Python wheel does not include the complete vault and examples.
2. Before opening the vault, download `main.js`, `manifest.json`, and `styles.css` from the [Advanced Canvas 7.0.0 release](https://github.com/Developer-Mike/obsidian-advanced-canvas/releases/tag/7.0.0). Put these three files directly in `.obsidian/plugins/advanced-canvas/`, keeping the supplied `data.json`. Advanced Canvas is installed separately, not distributed here.
3. Open the **project root as a vault** in desktop Obsidian. If a trust prompt appears, allow community plugins only if you trust the project and plugin code; otherwise use **Settings → Community plugins → Turn on community plugins**. Community plugins run with Obsidian's local permissions; review the local Proof Routing source before enabling it.
4. Confirm that the Canvas core plugin, **Advanced Canvas 7.0.0**, **Proof Routing 0.6.1**, and the **Appearance → CSS snippets → math-logic-mindmap** snippet are enabled. The supplied settings already select the community plugins and snippet; enable them if necessary. Open [the AM–GM map](mindmap/two-variable-am-gm.canvas) and click a node's detail link.

Reading examples needs **neither Python nor an AI assistant**. A GitHub file preview is not a Canvas viewer. To reproduce the verified environment, keep Advanced Canvas 7.0.0; installing from the community catalog or applying an update may select a newer, unreviewed version. Other readers offer basic viewing without all shapes and crossing bridges. See [Obsidian setup](docs/obsidian-setup.md) for detailed settings.

### ② Prepare the generation environment

Install **Python 3.11 or newer**, then run the following from the project root. Installation supplies `jsonschema>=4.18,<5`; no environment activation is needed.

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe skills/math-logic-mindmap/scripts/canvas_tool.py --help
```

If `python` opens an unusable Microsoft Store alias, create the environment with an installed `py -3.11` or your actual Python executable instead.

**macOS / Linux**

```sh
python3 -m venv .venv
./.venv/bin/python -m pip install -e .
./.venv/bin/python skills/math-logic-mindmap/scripts/canvas_tool.py --help
```

### ③ Ask for a new map

Open this folder in Codex, Claude Code, or another assistant that can read/write local files and run commands. If it does not load `AGENTS.md` or `CLAUDE.md`, ask it to read [the project Skill](skills/math-logic-mindmap/SKILL.md). Before generation, set `language` in [the config](math-logic-mindmap.config.json) to `en`, `fr`, or `zh-CN`; the supplied config is `en`. The new model's `presentation.language` and authored prose must match it. Changing the config does not translate existing maps.

> Prove that, for every positive integer n, the sum of the first n positive odd integers is n², and generate a proof logic map. Use this project's math-logic-mindmap Skill and configured language; independently complete the argument, validation, build, and release.

Review the assistant's plan before generation. The formal model is `proof/<slug>/<slug>.proof.json`, the map is `mindmap/<slug>.canvas`, and reading notes are in `note/<slug>/`. For your own problem, provide the statement, assumptions, preferred method, and reader level. [Maintenance](docs/maintenance.md) covers manual commands and upgrades.

## 3. Why this project exists

The project treats logic as a **first principle** of learning a proof. Starting from assumptions, definitions, and external mathematical tools, purposeful deductions and transformations let different paths flow naturally toward the statement to be proved. A reader can follow both what each step establishes and why it becomes useful at that point.

## 4. What makes it different

**The central question is how the “known” in a proof flows toward the “conclusion” through a series of purposeful inferences.** Many mind maps organize text into topics and levels. Their structure can resemble a table of contents: it tells us what a passage is about, but less often how earlier conditions produce a conclusion or why a particular step is chosen now. This project tries to show both the logical flow and the motivation behind the reasoning.

Assumptions, definitions, and external theorems form possible starting points. Intermediate results, transformations, case splits, constructions, and genuine combinations move the proof forward. Each connection makes a logical dependency traceable; detailed derivations and relationship notes explain how it is justified, while stage descriptions and operation notes also explain why the proof moves in that direction. An auxiliary object may prepare the conditions for a theorem, a reformulation may make the target familiar, and several intermediate results may meet to supply all the conditions a conclusion needs. These motivations turn the graph from an after-the-fact list of steps into something closer to the proof writer's sense of direction. The aim is a readable map of how the known becomes the conclusion and why the route was taken.

## 5. Examples

The bundled examples and screenshot are in English. Open them in Obsidian; a repository preview is not a Canvas viewer.

### Two-variable AM–GM

Open [the example Canvas](mindmap/two-variable-am-gm.canvas) and [its notes](note/two-variable-am-gm/index.md) for the complete argument.

![The English two-variable AM–GM proof map](docs/two-variable-am-gm.png)

Read downward: `K1` (nonnegative squares) and `A1` (nonnegative inputs) meet at `C1`, which derives the independent result `R1`: $(a+b)^2\ge 4ab$. Then `R1`, `A1`, and `K2` (square-root monotonicity) meet at `C2` and lead to `T1`, the target. This is why a `COMBINE` operation is followed by its own result card. This particular example has no `TRANSFORM` card; when used elsewhere, that operation appears as a downward triangle with the project CSS snippet.

### Irrationality of √2

Open [the contradiction-proof Canvas](mindmap/sqrt-2-irrationality.canvas) and [its notes](note/sqrt-2-irrationality/index.md). This example shows a temporary hypothesis, local witnesses, a contradiction, and the closure of their scopes before reaching the target.

In desktop Canvas, use **Ctrl + mouse wheel** to zoom (**Cmd + mouse wheel** on macOS) and **Shift + mouse wheel** to move horizontally; Canvas wheel settings may change this behavior.

## 6. Node guide

Type names are stable English identifiers in all language versions. A strict proof can start at an `ASSUMPTION`, `DEFINITION`, `KNOWN_RESULT`, or a scope-opening `HYPOTHESIS_LOCAL`; a local hypothesis must be discharged before the target. Every strict dependency is a visible flow toward one `TARGET`.

| Type | Meaning in a proof |
| --- | --- |
| `ASSUMPTION` | A given condition, such as a domain, sign, or range restriction. |
| `DEFINITION` | A definition or notation used in a later inference. |
| `KNOWN_RESULT` | An external theorem, lemma, or established rule actually used. |
| `CONSTRUCTION` | An auxiliary object deliberately built for the argument. |
| `CASE` | A circular operation that visibly splits into cases, later reconciled through `COMBINE`. |
| `LOCAL_INTRODUCTION` | An arbitrary value, witness, or other fixed local data introduced within a scope. |
| `HYPOTHESIS_LOCAL` | A temporary assumption, such as one made for contradiction or induction. |
| `DERIVATION` | A substantive local inference that advances the argument. |
| `LEMMA` | A useful intermediate proposition proved inside this argument. |
| `COMBINE` | A circle where independent required inputs join in one derivation; its conclusion is shown in a separate result or target card. |
| `TRANSFORM` | A downward triangle for a justified one-input operation, such as substitution or simplification; independent side conditions must be combined first. |
| `CONTRADICTION` | An explicit inconsistency used in an indirect proof. |
| `BOUND` | An established upper or lower bound. |
| `EXISTENCE_WITNESS` | A constructed object together with verification that it has the required property. |
| `TARGET` | The statement the proof is trying to establish. |
| `INTUITION` | Helpful explanation outside the strict proof; it cannot justify a proof step. |

The six configurable color roles are **external**, **combine**, **transform**, **result**, **target**, and **given**. They do not map one-to-one to the 16 types: `KNOWN_RESULT` or any `external: true` node uses external; `COMBINE` and `CASE` use combine; `TRANSFORM` uses transform; `TARGET` takes target before result; any `result: true` node uses result; strict `ASSUMPTION` and `LOCAL_INTRODUCTION` use given. Other nodes, including `DEFINITION` by default, have no role color. `INTUITION` has a transparent/default background and gray dashed border. Color is a reading aid, not proof validity.

## 7. Make it yours

Edit [`math-logic-mindmap.config.json`](math-logic-mindmap.config.json) before a new build. This example shows every supported key; choose your own six-digit hex colors:

```json
{
  "language": "en",
  "node_colors": {
    "external": "#B39DDB",
    "combine": "#E5C85B",
    "transform": "#D9DEE7",
    "result": "#CFE8CC",
    "target": "#E69A9A",
    "given": "#88BBDD"
  }
}
```

Without a config file, the defaults are Chinese and the original palette. The chosen language and colors are captured when a map is built; changing the global file does not change already published maps. A Markdown note's personal-additions area is preserved on regeneration. [Maintenance and recovery](docs/maintenance.md) explains how to keep manually adjusted layouts.

## 8. Read critically

An LLM may make mathematical mistakes or produce uneven explanations. A map's “Proved (mathematical conclusion)” label records the mathematical conclusion authored in its model; machine checks verify structure and file consistency, **not mathematical truth**. Visual review is separate and starts at `UNREVIEWED`.

For harder work, use the assistant's Plan mode to check the proof route, starting assumptions and tools, every applicability condition, and whether the node granularity suits your background. Intervene at this stage if the map would be too terse or too detailed; this can avoid wasting tokens on a map that does not help you learn. Afterwards, open node details and explanatory relationship notes and verify the derivation chain step by step. Consider another model or a human review; several iterations may be needed.

How far a stable, composable, human-readable graph language can express complex mathematical reasoning remains an open question. Formal machine representation of proofs is already quite mature. What remains uncertain is whether repeatable, testable abstraction rules can turn a strict proof into a bounded, readable graph without relying mainly on a designer's intuition and aesthetic judgment. A human-first design also introduces the uncertainty of different readers: the graph's expressive limits and granularity may not match someone's background, and a satisfactory version may take several attempts.

## 9. Vision

We hope readers will share the maps they create and that a future community will rate both correctness and readability, helping more people study proofs. The project does not currently provide a sharing or rating platform.

## 10. Future directions

The same approach may eventually visualize other problems with logical structure, such as algorithms, experimental procedures, and paper analysis. The current project and Skill are for mathematical proofs and problem solutions.

## Feedback

Report problems through [GitHub Issues](https://github.com/ShenglingZHU/math-logic-mindmap/issues), available once the repository is public and Issues are enabled. Include:

- The project version or Release/tag; if unknown, the download source and date.
- Your operating system and the relevant Python, Obsidian, Advanced Canvas, and Proof Routing versions.
- Reproduction steps, expected and actual behavior, and relevant errors.
- A minimal example: the input or model for generation problems; the necessary Canvas, notes, and screenshot for display problems.

Run the tool's `--version` using the same interpreter as above; find Obsidian's version under **Settings → About** and plugin versions in the community plugin list. For installation problems, also use that interpreter with `-m pip show math-logic-mindmap`.

Do not upload your whole personal vault. Check notes, screenshots, and logs for unrelated private content; you may anonymize usernames in paths while retaining the structure needed to reproduce the problem.

## Maintenance and license

For layout import, reviews, preview export, plugin synchronization, backups, deletion, and recovery, see [Maintenance and Recovery](docs/maintenance.md). The project is released under the [MIT License](LICENSE) by ZHU Shengling; external software and dependency boundaries are listed in [Third-Party Notices](THIRD_PARTY_NOTICES.md).
