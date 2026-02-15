from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:
    yaml = None


def _strip_fenced_yaml(text: str) -> str:
    if "```" not in text:
        return text
    lines = text.splitlines()
    start = None
    end = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("```"):
            if start is None:
                start = idx
            else:
                end = idx
                break
    if start is None or end is None or end <= start:
        return text
    body = lines[start + 1 : end]
    if body and body[0].strip().lower().startswith("yaml"):
        body = body[1:]
    return "\n".join(body)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if yaml is None or not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    text = _strip_fenced_yaml(text)
    try:
        data = yaml.safe_load(text) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _normalize_list_block(block: Any) -> dict[str, list[str]]:
    if not isinstance(block, dict):
        return {"primary": [], "spice": []}
    normalized: dict[str, list[str]] = {"primary": [], "spice": []}
    for key in ("primary", "spice"):
        items = block.get(key, [])
        if isinstance(items, list):
            normalized[key] = [str(item) for item in items if item]
    return normalized


def _merge_lists(target: dict[str, dict[str, list[str]]], source: dict[str, dict[str, list[str]]]) -> None:
    for media_type in ("movies", "tv"):
        for tier in ("primary", "spice"):
            existing = target[media_type][tier]
            for item in source[media_type][tier]:
                if item not in existing:
                    existing.append(item)


def load_user_prefs(base_dir: Path) -> dict[str, Any]:
    return _load_yaml_file(base_dir / ".userPrefs.yaml")


def load_list_prefs(base_dir: Path) -> dict[str, dict[str, list[str]]]:
    prefs = {
        "movies": {"primary": [], "spice": []},
        "tv": {"primary": [], "spice": []},
    }

    list_data = _load_yaml_file(base_dir / "UserPrefs_Lists.yaml")
    lists_root = list_data.get("lists", {}) if isinstance(list_data, dict) else {}
    merged = {
        "movies": _normalize_list_block(lists_root.get("movies")),
        "tv": _normalize_list_block(lists_root.get("tv")),
    }
    _merge_lists(prefs, merged)

    user_prefs = load_user_prefs(base_dir)
    trakt_lists = (
        user_prefs.get("trakt", {}).get("lists", {})
        if isinstance(user_prefs, dict)
        else {}
    )
    merged = {
        "movies": _normalize_list_block(trakt_lists.get("movies")),
        "tv": _normalize_list_block(trakt_lists.get("tv")),
    }
    _merge_lists(prefs, merged)

    return prefs


def get_trakt_user(base_dir: Path) -> str | None:
    user_prefs = load_user_prefs(base_dir)
    trakt = user_prefs.get("trakt", {}) if isinstance(user_prefs, dict) else {}
    user = trakt.get("user")
    return str(user) if user else None
