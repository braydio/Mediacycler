from __future__ import annotations

from dataclasses import replace

from shelf.model import ShelfItem, ShelfState, ShelfStatus
from shelf.store import load_state, save_state


def merge_scan(items: list[ShelfItem]) -> ShelfState:
    state = load_state()
    merged: dict[str, ShelfItem] = {}
    for item in items:
        existing = state.items.get(item.item_id)
        if existing:
            merged[item.item_id] = replace(
                item,
                status=existing.status,
            )
        else:
            merged[item.item_id] = item
    state.items = merged
    save_state(state)
    return state


def set_status(state: ShelfState, item_id: str, status: ShelfStatus) -> ShelfState:
    if item_id not in state.items:
        return state
    state.items[item_id] = replace(state.items[item_id], status=status)
    save_state(state)
    return state
