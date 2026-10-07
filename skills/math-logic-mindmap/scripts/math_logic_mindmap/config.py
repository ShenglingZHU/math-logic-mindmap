from __future__ import annotations

import json
import re
from pathlib import Path

from .common import Invalid, digest

CONFIG_NAME = "math-logic-mindmap.config.json"
DEFAULT_COLORS = {
    "external": "#B39DDB",
    "combine": "#E5C85B",
    "transform": "#D9DEE7",
    "result": "#CFE8CC",
    "target": "#E69A9A",
    "given": "#88BBDD",
}
DEFAULT_CONFIG = {"language": "zh-CN", "node_colors": DEFAULT_COLORS}
LANGUAGE_ALIASES = {
    "zh": "zh-CN", "zh-cn": "zh-CN",
    "en": "en", "en-us": "en",
    "fr": "fr", "fr-fr": "fr",
}
HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")


def normalize_language(value):
    if not isinstance(value, str):
        raise Invalid("CONFIG-LANGUAGE: language must be a string")
    key = value.strip().replace("_", "-").lower()
    if key not in LANGUAGE_ALIASES:
        raise Invalid("CONFIG-LANGUAGE: only zh-CN, en, fr, and their documented aliases are supported")
    return LANGUAGE_ALIASES[key]


def normalize_config(value=None):
    value = {} if value is None else value
    if not isinstance(value, dict):
        raise Invalid("CONFIG: the top level must be an object")
    unknown = set(value) - {"language", "node_colors"}
    if unknown:
        raise Invalid("CONFIG: unknown fields " + ", ".join(sorted(unknown)))
    colors = value.get("node_colors", {})
    if not isinstance(colors, dict):
        raise Invalid("CONFIG-COLOR: node_colors must be an object")
    unknown_colors = set(colors) - set(DEFAULT_COLORS)
    if unknown_colors:
        raise Invalid("CONFIG-COLOR: unknown node colors " + ", ".join(sorted(unknown_colors)))
    normalized_colors = dict(DEFAULT_COLORS)
    for role, color in colors.items():
        if not isinstance(color, str) or not HEX_COLOR.fullmatch(color):
            raise Invalid(f"CONFIG-COLOR {role}: must be a six-digit hexadecimal color #RRGGBB")
        normalized_colors[role] = color.upper()
    return {
        "language": normalize_language(value.get("language", "zh-CN")),
        "node_colors": normalized_colors,
    }


def load_config(root):
    root = Path(root).resolve()
    path = root / CONFIG_NAME
    if not path.exists():
        if (root / "math-proof-canvas.config.json").exists():
            raise Invalid(f"CONFIG-MIGRATION: rename math-proof-canvas.config.json to {CONFIG_NAME}")
        return normalize_config()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Invalid(f"CONFIG: cannot read {CONFIG_NAME}: {exc}") from exc
    return normalize_config(value)


def override_language(config, language=None):
    settings = normalize_config(config)
    if language is None:
        return settings
    return normalize_config({"language": language, "node_colors": settings["node_colors"]})


def config_hash(config):
    return digest(normalize_config(config))


def model_language(model):
    return normalize_language(model["presentation"]["language"])
