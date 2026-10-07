from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ID = re.compile(r"^[A-Z][A-Za-z0-9_]*$")
PERSONAL_TITLES = {"zh-CN": "个人补充", "en": "Personal notes", "fr": "Notes personnelles"}
PERSONAL = "\n## 个人补充\n<!-- personal:start -->\n"
PERSONAL_END = "<!-- personal:end -->\n"
CONTEXT = ["领域", "背景", "角色 / 重要性", "作用", "证明思路/策略", "证明工具"]


class Invalid(ValueError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.replace("\r\n", "\n").rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(path, data):
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def digest(data):
    if isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()
    return digest(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def file_hash(path):
    return digest(Path(path).read_bytes())


def safe(root, relative):
    root = Path(root).resolve()
    relative = str(relative)
    if "\\" in relative or ":" in relative or relative.startswith("/"):
        raise Invalid(f"Unsafe path: {relative}")
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or target == root:
        raise Invalid(f"Path escapes the project root: {relative}")
    return target


def slug_value(value):
    if not SLUG.fullmatch(value):
        raise Invalid("slug must contain lowercase ASCII letters, digits, and hyphens only")
    return value


def personal(text):
    start = "<!-- personal:start -->\n"
    if text.count(start) != 1 or text.count(PERSONAL_END) != 1:
        raise Invalid("Personal-notes boundaries are missing or duplicated")
    prefix, tail = text.split(start)
    heading = re.search(r"\n## [^\n]+\n$", prefix)
    if not heading:
        raise Invalid("Personal-notes heading is missing")
    before = prefix[:heading.start()]
    notes, after = tail.split(PERSONAL_END)
    if after.strip():
        raise Invalid("Unmanaged content exists after the personal-notes region")
    return before, notes


def managed_hash(path):
    path = Path(path)
    if path.suffix == ".md" and path.name != "_review-checklist.md":
        return digest(personal(path.read_text(encoding="utf-8"))[0].encode())
    return file_hash(path)


def wiki(path, label, heading=""):
    return f"[[{path}{'#' + heading if heading else ''}|{label}]]"


def inline(latex):
    return "$" + latex + "$"


def table_cell(text):
    # Markdown escaping is a separate layer; math authors must use semantic TeX bars.
    return str(text).replace("|", "\\|").replace("\n", " ")


def personal_delimiter(language="zh-CN"):
    if language not in PERSONAL_TITLES:
        raise Invalid(f"Unsupported personal-notes language: {language}")
    return "\n## " + PERSONAL_TITLES[language] + "\n<!-- personal:start -->\n"


def notebook(text, language="zh-CN"):
    return text.rstrip() + "\n" + personal_delimiter(language) + PERSONAL_END
