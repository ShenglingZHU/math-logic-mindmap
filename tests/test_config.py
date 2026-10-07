"""User configuration, localization, and frozen-presentation regressions."""
import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/math-logic-mindmap/scripts"))

from math_logic_mindmap import bundle
from math_logic_mindmap.cli import main
from math_logic_mindmap.common import Invalid, PERSONAL, PERSONAL_END, digest, managed_hash, write_json, write_text
from math_logic_mindmap.config import DEFAULT_COLORS, config_hash, load_config, normalize_config, override_language
from math_logic_mindmap.i18n import CATALOGS, reserved_headings
from math_logic_mindmap.model import node_color, validate
from math_logic_mindmap.render import generate_notes, layout


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.model = json.loads((ROOT / "tests/fixtures/canonical-smoke.proof.json").read_text(encoding="utf-8"))

    def test_defaults_aliases_partial_colors_and_hash_are_canonical(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(load_config(directory), {"language": "zh-CN", "node_colors": DEFAULT_COLORS})
        for source, expected in [("zh", "zh-CN"), ("ZH_cn", "zh-CN"), ("en-US", "en"), ("fr_FR", "fr")]:
            with self.subTest(source=source):
                config = normalize_config({"language": source, "node_colors": {"target": "#abcdef"}})
                self.assertEqual(config["language"], expected)
                self.assertEqual(config["node_colors"]["target"], "#ABCDEF")
                self.assertEqual(config_hash(config), config_hash(normalize_config(config)))

    def test_cli_prioritizes_math_warnings_without_mutating_full_report(self):
        warnings = [
            'LAYOUT first',
            'SYMBOL second',
            'MATH-INLINE-RISK model/a: first math',
            'LAYOUT third',
            'LAYOUT fourth',
            'LAYOUT fifth',
            'LAYOUT sixth',
            'LAYOUT seventh',
            'LAYOUT eighth',
            'MATH-INLINE-RISK model/b: second math',
        ]
        report = {'machine': 'PASS', 'warnings': list(warnings)}
        with tempfile.TemporaryDirectory() as directory, \
                patch('math_logic_mindmap.cli.sync_skills', return_value=report):
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(['--root', directory, 'check-skill-sync'])
        self.assertEqual(code, 0)
        console = json.loads(output.getvalue())
        self.assertEqual(console['warning_count'], len(warnings))
        self.assertEqual(len(console['warnings']), 8)
        self.assertEqual(console['warnings'][:2], [warnings[2], warnings[9]])
        self.assertEqual(console['warnings'][2:], warnings[:2] + warnings[3:7])
        self.assertEqual(report['warnings'], warnings)

    def test_cli_keeps_granularity_warning_when_console_output_is_truncated(self):
        review = 'GRANULARITY-REVIEW: unreviewed merge candidates=1 [D1]; stale review IDs=0 [-]'
        warnings = [f'MATH-INLINE-RISK model/{i}: review' for i in range(9)] + [review]
        report = {'machine': 'PASS', 'warnings': list(warnings)}
        with tempfile.TemporaryDirectory() as directory, \
                patch('math_logic_mindmap.cli.sync_skills', return_value=report):
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(['--root', directory, 'check-skill-sync'])
        self.assertEqual(code, 0)
        console = json.loads(output.getvalue())
        self.assertEqual(console['warning_count'], 10)
        self.assertEqual(console['warnings'], warnings[:7] + [review])
        self.assertEqual(report['warnings'], warnings)

    def test_invalid_configuration_fails_closed(self):
        invalid = [
            {"unknown": True},
            {"language": "de"},
            {"node_colors": {"edge": "#112233"}},
            {"node_colors": {"target": "#abc"}},
            {"node_colors": {"target": "1"}},
            {"node_colors": {"target": 123}},
        ]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(Invalid):
                normalize_config(value)
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "math-logic-mindmap.config.json").write_text("{", encoding="utf-8")
            with self.assertRaises(Invalid):
                load_config(directory)

    def test_legacy_configuration_requires_rename_before_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = root / "math-proof-canvas.config.json"
            new = root / "math-logic-mindmap.config.json"
            write_json(old, {"language": "en"})
            with self.assertRaisesRegex(Invalid, "CONFIG-MIGRATION.*math-logic-mindmap.config.json"):
                load_config(root)

            proof = root / "proof/canonical-smoke/canonical-smoke.proof.json"
            write_json(proof, self.model)
            output = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(output):
                code = main(["--root", str(root), "build", "proof/canonical-smoke/canonical-smoke.proof.json"])
            self.assertEqual(code, 1)
            self.assertIn("CONFIG-MIGRATION", output.getvalue())
            self.assertFalse((root / ".build/staging/canonical-smoke").exists())
            self.assertFalse((root / "mindmap/canonical-smoke.canvas").exists())

            write_json(new, {"language": "fr"})
            self.assertEqual(load_config(root)["language"], "fr")
            new.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(Invalid, "cannot read math-logic-mindmap.config.json"):
                load_config(root)

    def test_model_language_is_stable_and_build_requires_match(self):
        validate(self.model)
        missing = copy.deepcopy(self.model)
        missing['presentation'].pop('language')
        with self.assertRaisesRegex(Invalid, 'language'):
            validate(missing)
        english = copy.deepcopy(self.model)
        english["presentation"]["language"] = "en"
        validate(english)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "proof/canonical-smoke/canonical-smoke.proof.json"
            write_json(path, english)
            with self.assertRaisesRegex(Invalid, "CONFIG-LANGUAGE"):
                bundle.build(root, path)
        broken = copy.deepcopy(self.model)
        broken["presentation"]["language"] = "de"
        with self.assertRaises(Invalid):
            validate(broken)

    def test_english_build_freezes_config_across_global_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = copy.deepcopy(self.model)
            model["presentation"]["language"] = "en"
            proof = root / "proof/canonical-smoke/canonical-smoke.proof.json"
            write_json(proof, model)
            config = {"language": "en-US", "node_colors": {"target": "#123abc"}}
            write_json(root / "math-logic-mindmap.config.json", config)
            bundle.build(root, proof)
            stage = root / ".build/staging/canonical-smoke"
            frozen = json.loads((stage / "render-config.json").read_text(encoding="utf-8"))
            self.assertEqual(frozen["language"], "en")
            self.assertEqual(frozen["node_colors"]["target"], "#123ABC")
            canvas = json.loads((stage / "mindmap/canonical-smoke.canvas").read_text(encoding="utf-8"))
            self.assertEqual(canvas["metadata"]["proofPresentation"]["configHash"], config_hash(frozen))
            target = next(node for node in canvas["nodes"] if node["id"] == model["target_id"])
            self.assertEqual(target["color"], "#123ABC")
            self.assertEqual(target["styleAttributes"]["proofColorRole"], "target")
            self.assertEqual(target["styleAttributes"]["proofPaletteDefault"], "false")
            note = (stage / "note/canonical-smoke/A1.md").read_text(encoding="utf-8")
            self.assertIn("lang: en", note)
            self.assertIn("## Navigation", note)
            write_json(root / "math-logic-mindmap.config.json", {"language": "fr"})
            bundle.release(root, "canonical-smoke")
            manifest = json.loads((root / "proof/canonical-smoke/canonical-smoke.manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_config"], frozen)
            self.assertEqual(bundle.status(root, "canonical-smoke")["machine"], "PASS")

    def test_personal_hash_and_cross_language_release_are_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sample = root / "note.md"
            write_text(sample, "managed" + PERSONAL + "keep me\n" + PERSONAL_END)
            self.assertEqual(managed_hash(sample), digest(b"managed"))

            proof = root / "proof/canonical-smoke/canonical-smoke.proof.json"
            write_json(proof, self.model)
            bundle.build(root, proof)
            bundle.release(root, "canonical-smoke")
            note = root / "note/canonical-smoke/A1.md"
            note.write_text(note.read_text(encoding="utf-8").replace(PERSONAL_END, "keep this\n" + PERSONAL_END), encoding="utf-8")

            translated = copy.deepcopy(self.model)
            translated["presentation"]["language"] = "en"
            write_json(proof, translated)
            write_json(root / "math-logic-mindmap.config.json", {"language": "en"})
            bundle.build(root, proof)
            bundle.release(root, "canonical-smoke")
            changed = note.read_text(encoding="utf-8")
            self.assertIn("## Personal notes", changed)
            self.assertIn("keep this", changed)
            self.assertNotIn("## 个人补充", changed)

    def test_all_locales_render_safe_reserved_headings(self):
        from math_logic_mindmap.i18n import RESERVED_KEYS
        expected = sum(len({catalog[key] for key in RESERVED_KEYS}) for catalog in CATALOGS.values())
        self.assertLessEqual(len(reserved_headings()), expected)
        for language in ("zh-CN", "en", "fr"):
            model = copy.deepcopy(self.model)
            model["presentation"]["language"] = language
            config = normalize_config({"language": language})
            notes = generate_notes(model, config)
            canvas = layout(model, validate(model), config=config)
            self.assertTrue(notes)
            self.assertEqual(canvas["metadata"]["proofPresentation"]["language"], language)

    def test_theme_css_and_routing_label_measurement_use_configurable_color_and_real_width(self):
        css = (ROOT / ".obsidian/snippets/math-logic-mindmap.css").read_text(encoding="utf-8")
        self.assertIn('data-proof-palette-default="true"', css)
        self.assertIn('data-proof-palette-default="false"', css)
        expected_mix = {
            "combine": ("20%", "15%"), "transform": ("100%", "15%"),
            "result": ("53%", "8%"), "external": ("19%", "15%"),
            "target": ("21%", "14%"), "given": ("17%", "15%"),
        }
        for role, (light, dark) in expected_mix.items():
            self.assertIn(f'data-proof-color-role="{role}"] {{ --proof-color-mix-light: {light}; --proof-color-mix-dark: {dark}; }}', css)
        self.assertNotIn("var(--canvas-color) 18%", css)
        self.assertNotIn("var(--canvas-color) 24%", css)
        self.assertIn("#fff7d6", css)  # Existing default light-theme appearance is retained.
        plugin = (ROOT / "plugins/proof-routing/main.js").read_text(encoding="utf-8")
        self.assertIn("getComputedTextLength", plugin)
        self.assertNotIn("edge.label.length*18", plugin)
        self.assertIn("delete window.require.cache[resolved]", plugin)
        self.assertIn("const d = edge.path", plugin)
        self.assertNotIn("core.svg", plugin)
        self.assertIn("data-proof-labels", plugin)
        self.assertIn("core.resolveLabels", plugin)
        self.assertIn("measureLayer.remove()", plugin)
        self.assertLess(plugin.index("for (const edge of resolved.routes) this.drawPath"),
                        plugin.index("for (const spec of resolved.labels)"))

    def test_public_obsidian_configuration_is_minimal_and_exact(self):
        self.assertEqual(json.loads((ROOT / ".obsidian/appearance.json").read_text(encoding="utf-8")),
                         {"enabledCssSnippets": ["math-logic-mindmap"]})
        self.assertEqual(json.loads((ROOT / ".obsidian/community-plugins.json").read_text(encoding="utf-8")),
                         ["advanced-canvas", "proof-routing"])
        self.assertEqual(json.loads((ROOT / ".obsidian/plugins/advanced-canvas/data.json").read_text(encoding="utf-8")), {
            "nodeStylingFeatureEnabled": True,
            "edgesStylingFeatureEnabled": True,
            "autoFileNodeEdgesFeatureEnabled": False,
            "autoResizeNodeFeatureEnabled": False,
            "autoResizeNodeEnabledByDefault": False,
        })

    def test_proof_routing_cli_preview_check_and_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("manifest.json", "main.js", "geometry-core.cjs"):
                path = root / "plugins/proof-routing" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("source:" + name + "\n", encoding="utf-8")

            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["--root", directory, "sync-proof-routing"]), 0)
            self.assertEqual(json.loads(out.getvalue())["mode"], "preview")
            self.assertFalse((root / ".obsidian/plugins/proof-routing").exists())

            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["--root", directory, "check-proof-routing-sync"]), 1)
            self.assertEqual(json.loads(out.getvalue())["status"], "FAIL")

            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["--root", directory, "sync-proof-routing",
                                       "--confirm", "proof-routing"]), 0)
            self.assertEqual(json.loads(out.getvalue())["status"], "PASS")

            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["--root", directory, "check-proof-routing-sync"]), 0)
            self.assertEqual(json.loads(out.getvalue())["status"], "PASS")

    def test_localized_generated_punctuation(self):
        chinese = generate_notes(self.model, {"language": "zh-CN"})
        c1 = next(node for node in self.model["nodes"] if node["id"] == "C1")
        self.assertIn(f"|C1 · {c1['title']}]]：{c1['navigation']['role']}", chinese["note/canonical-smoke/A1.md"])
        self.assertIn("数学状态：已证明（数学结论）；证明标准：`strict`。", chinese["note/canonical-smoke/index.md"])
        self.assertIn("视觉状态：**UNREVIEWED**", bundle.checklist("canonical-smoke", config={"language": "zh-CN"}))

        detailed = copy.deepcopy(self.model)
        edge = detailed["edges"][0]
        edge["detail_mode"] = "EDGE_DETAIL"
        edge["label_text"] = "条件传递"
        edge["detail"] = {"summary": "摘要", "source_contribution": "贡献", "transition_steps": ["转换"],
                          "target_gain": "所得", "conditions": ["条件甲"], "condition_checks": ["已核验"],
                          "role_in_proof": "作用"}
        edge_path = f"note/canonical-smoke/{edge['id']}.md"
        chinese_edge = generate_notes(detailed, {"language": "zh-CN"})[edge_path]
        self.assertIn("`ASSUMPTION`；$", chinese_edge)
        self.assertIn("- 条件甲：已核验", chinese_edge)

        for language, status_line, checklist_line in [
            ("en", "Mathematical status: Proved (mathematical conclusion); Proof standard: `strict`.", "Visual status: **UNREVIEWED**"),
            ("fr", "Statut mathématique : Démontré (conclusion mathématique) ; Niveau de preuve : `strict`.", "Statut visuel : **UNREVIEWED**"),
        ]:
            notes = generate_notes(self.model, {"language": language})
            self.assertIn(status_line, notes["note/canonical-smoke/index.md"])
            self.assertIn(checklist_line, bundle.checklist("canonical-smoke", config={"language": language}))
        english_edge = generate_notes(detailed, {"language": "en"})[edge_path]
        french_edge = generate_notes(detailed, {"language": "fr"})[edge_path]
        self.assertIn("`ASSUMPTION`; $", english_edge)
        self.assertIn("- 条件甲: 已核验", english_edge)
        self.assertIn("`ASSUMPTION` ; $", french_edge)
        self.assertIn("- 条件甲 : 已核验", french_edge)

        with_binding = copy.deepcopy(self.model)
        with_binding["nodes"][0]["bindings"] = [{"id": "u", "symbol_latex": "u",
                                                "domain_latex": r"\mathbb{Z}", "depends_on": []}]
        for language, separator in [("zh-CN", "："), ("en", ": "), ("fr", " : ")]:
            note = generate_notes(with_binding, {"language": language})["note/canonical-smoke/A1.md"]
            self.assertIn(f"- $u${separator}$\\mathbb{{Z}}$", note)

    def test_build_language_override_keeps_config_colors_and_freezes_effective_language(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proof = root / "proof/canonical-smoke/canonical-smoke.proof.json"
            write_json(proof, self.model)
            config_path = root / "math-logic-mindmap.config.json"
            write_json(config_path, {"language": "en", "node_colors": {"target": "#123abc"}})
            original_config = config_path.read_bytes()
            with self.assertRaisesRegex(Invalid, "--language <model language>"):
                bundle.build(root, proof)

            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = main(["--root", str(root), "build", "proof/canonical-smoke/canonical-smoke.proof.json",
                             "--language", "zh"])
            self.assertEqual(code, 0, err.getvalue())
            self.assertEqual(config_path.read_bytes(), original_config)
            frozen = json.loads((root / ".build/staging/canonical-smoke/render-config.json").read_text(encoding="utf-8"))
            self.assertEqual(frozen["language"], "zh-CN")
            self.assertEqual(frozen["node_colors"]["target"], "#123ABC")
            bundle.release(root, "canonical-smoke")
            manifest = json.loads((root / "proof/canonical-smoke/canonical-smoke.manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["render_config"], frozen)
            with self.assertRaises(Invalid):
                override_language(load_config(root), "de")

    def test_each_role_accepts_a_near_default_custom_color(self):
        changed = {role: color[:-1] + ("0" if color[-1] != "0" else "1") for role, color in DEFAULT_COLORS.items()}
        settings = normalize_config({"node_colors": changed})
        canvas = layout(self.model, validate(self.model), config=settings)
        for node in canvas["nodes"]:
            role = node.get("styleAttributes", {}).get("proofColorRole")
            if role:
                self.assertEqual(node["color"], changed[role])
                self.assertEqual(node["styleAttributes"]["proofPaletteDefault"], "false")
        role_nodes = {
            "external": {"type": "KNOWN_RESULT"}, "combine": {"type": "COMBINE"},
            "transform": {"type": "TRANSFORM"}, "result": {"type": "LEMMA", "result": True},
            "target": {"type": "TARGET"}, "given": {"type": "ASSUMPTION"},
        }
        for role, node in role_nodes.items():
            self.assertEqual(node_color(node, settings), changed[role])
        self.assertEqual(override_language(settings, "en-US")["language"], "en")


if __name__ == "__main__":
    unittest.main()
