"""Active topics are removable without coupling system tests to published content."""
import ast
import copy
import hashlib
import io
import os
import shutil
import subprocess
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/math-logic-mindmap/scripts'))
from math_logic_mindmap import bundle
from math_logic_mindmap.cli import main
from math_logic_mindmap.common import Invalid, PERSONAL, PERSONAL_END, read_json, write_json, write_text


class TopicRemovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def make_topic(self, slug='foo'):
        model = copy.deepcopy(read_json(ROOT / 'tests/fixtures/canonical-smoke.proof.json'))
        model['slug'] = slug
        path = self.root / 'proof' / slug / f'{slug}.proof.json'
        write_json(path, model)
        return model, path

    def test_preview_reports_manual_content_without_writing(self):
        proof = self.root / 'proof/foo'
        note = self.root / 'note/foo'
        write_text(proof / 'foo.proof.json', '{}')
        write_text(proof / 'foo.math-review.json', '{}')
        write_text(proof / 'extra.txt', 'extra')
        write_text(note / 'A1.md', 'managed' + PERSONAL + 'keep me\n' + PERSONAL_END)
        write_text(note / 'manual.md', 'manual')
        write_text(note / 'assets/diagram.png', 'image bytes')
        write_json(proof / 'foo.manifest.json', {'artifacts': {'note/foo/A1.md': 'hash'}})
        backup = self.root / '.build/backups/foo/20260913T120000000000Z'
        write_text(backup / 'manifest.json', '{}')
        before = {p.relative_to(self.root).as_posix(): p.read_bytes()
                  for p in self.root.rglob('*') if p.is_file()}
        result = bundle.remove_topic(self.root, 'foo')
        after = {p.relative_to(self.root).as_posix(): p.read_bytes()
                 for p in self.root.rglob('*') if p.is_file()}
        self.assertEqual(result['mode'], 'preview')
        self.assertEqual(before, after)
        self.assertEqual(result['warnings']['personal_notes'], ['note/foo/A1.md'])
        self.assertIn('note/foo/manual.md', result['warnings']['unmanaged_note_files'])
        self.assertIn('note/foo/assets/diagram.png', result['warnings']['unmanaged_note_files'])
        self.assertIn('proof/foo/foo.math-review.json', result['warnings']['review_files'])
        self.assertIn('proof/foo/extra.txt', result['warnings']['unexpected_proof_files'])
        self.assertIsNotNone(result['warnings']['retained_backup'])
        self.assertNotIn('material_notice', result['warnings'])

    def test_preview_distinguishes_personal_formatting_and_managed_edits(self):
        _, path = self.make_topic('foo')
        bundle.build(self.root, path)
        bundle.release(self.root, 'foo')
        note_path = self.root / 'note/foo/A1.md'
        canvas_path = self.root / 'mindmap/foo.canvas'

        note_text = note_path.read_text(encoding='utf-8')
        note_path.write_text(note_text.replace(PERSONAL, PERSONAL + 'personal only\n'), encoding='utf-8')
        canvas = read_json(canvas_path)
        canvas['nodes'].reverse()
        canvas['edges'].reverse()
        write_json(canvas_path, canvas)
        preview = bundle.remove_topic(self.root, 'foo')
        self.assertNotIn('note/foo/A1.md', preview['warnings']['modified_managed_files'])
        self.assertNotIn('mindmap/foo.canvas', preview['warnings']['modified_managed_files'])

        note_path.write_text(note_path.read_text(encoding='utf-8').replace('待除不等式', '手工修改标题', 1),
                             encoding='utf-8')
        canvas = read_json(canvas_path)
        next(node for node in canvas['nodes'] if node['id'] == 'A1')['text'] += '\n手工修改'
        write_json(canvas_path, canvas)
        preview = bundle.remove_topic(self.root, 'foo')
        self.assertIn('note/foo/A1.md', preview['warnings']['modified_managed_files'])
        self.assertIn('mindmap/foo.canvas', preview['warnings']['modified_managed_files'])

    def test_preview_rejects_manifest_paths_outside_current_topic(self):
        outside = self.root / 'outside.txt'
        write_text(outside, 'must not be inspected')
        write_json(self.root / 'proof/foo/foo.manifest.json', {
            'artifacts': {},
            'managed_hashes': {
                '../outside.txt': 'invalid',
                'note/foo/../../outside.txt': 'invalid',
                'note/foo/missing.md': 'missing',
            },
        })
        result = bundle.remove_topic(self.root, 'foo')
        errors = result['warnings']['managed_file_check_errors']
        self.assertEqual([item['path'] for item in errors], ['../outside.txt', 'note/foo/../../outside.txt'])
        self.assertEqual(outside.read_text(encoding='utf-8'), 'must not be inspected\n')

    def test_confirmation_mismatch_is_cli_failure_without_deletion(self):
        write_text(self.root / 'proof/foo/foo.proof.json', '{}')
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(['--root', str(self.root), 'remove-topic', 'foo', '--confirm', 'foo-bar'])
        self.assertEqual(code, 1)
        self.assertIn('REMOVE-CONFIRM', err.getvalue())
        self.assertTrue((self.root / 'proof/foo/foo.proof.json').is_file())

    def test_exact_work_match_and_idempotence(self):
        exact = self.root / '.build/work/foo-aaaaaaaaaaaa'
        neighbour = self.root / '.build/work/foo-bar-bbbbbbbbbbbb'
        malformed = self.root / '.build/work/foo-not-a-hash'
        for path in (exact, neighbour, malformed):
            write_text(path / 'marker', path.name)
        write_text(self.root / 'mindmap/foo.canvas.math-logic-mindmap-tmp', 'temporary')
        first = bundle.remove_topic(self.root, 'foo', 'foo')
        self.assertEqual(first['status'], 'PASS')
        self.assertFalse(exact.exists())
        self.assertFalse((self.root / 'mindmap/foo.canvas.math-logic-mindmap-tmp').exists())
        self.assertTrue(neighbour.is_dir())
        self.assertTrue(malformed.is_dir())
        second = bundle.remove_topic(self.root, 'foo', 'foo')
        self.assertEqual(second['status'], 'PASS')
        self.assertEqual(second['removed'], [])

    def test_reparse_target_is_rejected(self):
        write_text(self.root / 'proof/foo/foo.proof.json', '{}')
        with patch('math_logic_mindmap.bundle._is_reparse_point', return_value=True):
            with self.assertRaisesRegex(Invalid, 'REMOVE-REPARSE'):
                bundle.remove_topic(self.root, 'foo', 'foo')
        self.assertTrue((self.root / 'proof/foo/foo.proof.json').is_file())

    def test_partial_failure_stops_before_proof_source(self):
        work = self.root / '.build/work/foo-aaaaaaaaaaaa'
        stage = self.root / '.build/staging/foo'
        write_text(work / 'marker', 'work')
        write_text(stage / 'marker', 'stage')
        write_text(self.root / 'proof/foo/foo.proof.json', '{}')
        original = bundle.shutil.rmtree
        injected = False

        def fail_stage(path):
            nonlocal injected
            if Path(path).resolve() == stage.resolve():
                injected = True
                raise PermissionError('in use')
            return original(path)

        with patch('math_logic_mindmap.bundle.shutil.rmtree', side_effect=fail_stage):
            result = bundle.remove_topic(self.root, 'foo', 'foo')
        self.assertTrue(injected)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('.build/work/foo-aaaaaaaaaaaa', result['removed'])
        self.assertNotIn('.build/staging/foo', result['removed'])
        self.assertEqual(result['failed_path'], '.build/staging/foo')
        self.assertTrue(stage.is_dir())
        self.assertEqual((stage / 'marker').read_text(encoding='utf-8'), 'stage\n')
        self.assertTrue((self.root / 'proof/foo/foo.proof.json').is_file())

    def test_release_remove_and_recreate_same_slug(self):
        model, path = self.make_topic('cycle-smoke')
        bundle.build(self.root, path)
        bundle.release(self.root, 'cycle-smoke')
        self.assertEqual(bundle.status(self.root, 'cycle-smoke')['machine'], 'PASS')
        source = path.read_bytes()
        removed = bundle.remove_topic(self.root, 'cycle-smoke', 'cycle-smoke')
        self.assertEqual(removed['status'], 'PASS')
        for relative in ('proof/cycle-smoke', 'note/cycle-smoke',
                         'mindmap/cycle-smoke.canvas', '.build/staging/cycle-smoke'):
            self.assertFalse((self.root / relative).exists())
        path.parent.mkdir(parents=True)
        path.write_bytes(source)
        bundle.build(self.root, path)
        bundle.release(self.root, 'cycle-smoke')
        self.assertEqual(bundle.status(self.root, 'cycle-smoke')['machine'], 'PASS')


class TopicBoundaryTests(unittest.TestCase):
    @staticmethod
    def _literal_prefix(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr) and node.values:
            first = node.values[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                return first.value
        return None

    @classmethod
    def _root_first_segment(cls, node):
        if isinstance(node, ast.Name) and node.id == 'ROOT':
            return ''
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            first = cls._root_first_segment(node.left)
            if first is None:
                return None
            if first:
                return first
            literal = cls._literal_prefix(node.right)
            return literal.replace('\\', '/').split('/')[0] if literal else None
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'joinpath'
                and isinstance(node.func.value, ast.Name) and node.func.value.id == 'ROOT'
                and node.args):
            literal = cls._literal_prefix(node.args[0])
            return literal.replace('\\', '/').split('/')[0] if literal else None
        return None

    def test_tests_do_not_read_repository_topic_roots(self):
        forbidden = {'proof', 'mindmap', 'note'}
        violations = []
        for path in sorted((ROOT / 'tests').glob('test_*.py')):
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            for node in ast.walk(tree):
                first = self._root_first_segment(node)
                if first in forbidden:
                    violations.append(f'{path.name}:{node.lineno}:{first}')
        self.assertEqual(violations, [])

    def test_system_only_copy_runs_full_suite_and_topic_lifecycle(self):
        if os.environ.get('MATH_LOGIC_MINDMAP_SYSTEM_ONLY_CHILD') == '1':
            self.skipTest('The isolated-copy subtest does not recursively create a second copy.')

        def copy_tree(source, destination):
            shutil.copytree(source, destination,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

        def system_hashes(root):
            excluded = {'proof', 'mindmap', 'note', '.build'}
            result = {}
            for path in root.rglob('*'):
                relative = path.relative_to(root)
                if (not path.is_file() or relative.parts[0] in excluded
                        or '__pycache__' in relative.parts or path.suffix == '.pyc'):
                    continue
                result[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
            return result

        with tempfile.TemporaryDirectory() as directory:
            isolated = Path(directory) / 'system-only'
            isolated.mkdir()
            for relative in ('skills/math-logic-mindmap', 'plugins', 'tests', 'docs',
                             '.agents', '.claude'):
                source = ROOT / relative
                if source.exists():
                    copy_tree(source, isolated / relative)
            for relative in ('.obsidian/plugins/proof-routing',):
                copy_tree(ROOT / relative, isolated / relative)
            for relative in ('.obsidian/snippets/math-logic-mindmap.css',
                             '.obsidian/appearance.json', '.obsidian/community-plugins.json',
                             '.obsidian/plugins/advanced-canvas/data.json'):
                (isolated / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, isolated / relative)
            for relative in ('AGENTS.md', 'CLAUDE.md', 'README.md', 'pyproject.toml',
                             'setup.py', 'uv.lock', '.editorconfig', '.gitignore',
                             '.gitattributes', 'LICENSE', 'THIRD_PARTY_NOTICES.md'):
                source = ROOT / relative
                if source.is_file():
                    (isolated / relative).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, isolated / relative)

            for forbidden in ('proof', 'mindmap', 'note', '.build'):
                self.assertFalse((isolated / forbidden).exists())
            before = system_hashes(isolated)
            env = os.environ.copy()
            env['MATH_LOGIC_MINDMAP_SYSTEM_ONLY_CHILD'] = '1'
            env['PYTHONUTF8'] = '1'

            suite = subprocess.run(
                [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'],
                cwd=isolated, env=env, text=True, encoding='utf-8', errors='replace',
                capture_output=True, timeout=180,
            )
            self.assertEqual(suite.returncode, 0, suite.stdout + suite.stderr)

            tool = isolated / 'skills/math-logic-mindmap/scripts/canvas_tool.py'

            def run_tool(*arguments):
                completed = subprocess.run(
                    [sys.executable, '-B', str(tool), *arguments], cwd=isolated, env=env,
                    text=True, encoding='utf-8', errors='replace', capture_output=True, timeout=60,
                )
                self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
                return completed

            run_tool('check-skill-sync')
            slug = 'isolation-smoke'
            source_model = read_json(isolated / 'tests/fixtures/canonical-smoke.proof.json')
            source_model['slug'] = slug
            model_path = isolated / f'proof/{slug}/{slug}.proof.json'
            write_json(model_path, source_model)
            model_relative = f'proof/{slug}/{slug}.proof.json'
            run_tool('validate-model', model_relative)
            run_tool('build', model_relative)
            run_tool('validate-bundle', model_relative, '--bundle', f'.build/staging/{slug}')
            run_tool('release', slug)
            self.assertIn('"machine": "PASS"', run_tool('status', slug).stdout)
            run_tool('remove-topic', slug)
            run_tool('remove-topic', slug, '--confirm', slug)
            for relative in (f'proof/{slug}', f'note/{slug}', f'mindmap/{slug}.canvas',
                             f'.build/staging/{slug}', f'.build/backups/{slug}'):
                self.assertFalse((isolated / relative).exists(), relative)

            write_json(model_path, source_model)
            run_tool('validate-model', model_relative)
            run_tool('build', model_relative)
            run_tool('validate-bundle', model_relative, '--bundle', f'.build/staging/{slug}')
            run_tool('release', slug)
            self.assertIn('"machine": "PASS"', run_tool('status', slug).stdout)
            self.assertEqual(system_hashes(isolated), before)


if __name__ == '__main__':
    unittest.main()
