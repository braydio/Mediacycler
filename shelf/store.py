from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Any

from shelf.model import ShelfItem, ShelfState


def _default_store_path() -> str:
    path = os.getenv("SHELF_STORE_PATH")
    if path:
        return os.path.expanduser(path)
    return os.path.expanduser("~/.cache/mediacycler/shelf_state.json")


def load_state() -> ShelfState:
    path = _default_store_path()
    if not os.path.exists(path):
        return ShelfState()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return ShelfState()
    items: dict[str, ShelfItem] = {}
    for item_id, payload in raw.get("items", {}).items():
        if not isinstance(payload, dict):
            continue
        items[item_id] = ShelfItem(
            item_id=item_id,
            title=payload.get("title", ""),
            path=payload.get("path", ""),
            kind=payload.get("kind", "movie"),
            size_bytes=int(payload.get("size_bytes", 0)),
            last_modified=float(payload.get("last_modified", 0.0)),
            download_completed_at=(
                float(payload["download_completed_at"])
                if payload.get("download_completed_at") is not None
                else None
            ),
            poster_url=payload.get("poster_url"),
            genres=list(payload.get("genres", []) or []),
            status=payload.get("status", "undecided"),
        )
    return ShelfState(version=int(raw.get("shelf_version", 1)), items=items)


def save_state(state: ShelfState) -> None:
    path = _default_store_path()
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    payload: dict[str, Any] = {
        "shelf_version": state.version,
        "items": {},
    }
    for item_id, item in state.items.items():
        data = asdict(item)
        data.pop("item_id", None)
        payload["items"][item_id] = data
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
