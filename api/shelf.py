"""Shelf API skeleton.

This module defines the web-shaped contract but does not bind to any web framework yet.
"""
from __future__ import annotations

from dataclasses import asdict
from urllib.parse import quote

from shelf.decisions import merge_scan, set_status
from shelf.executor import apply_deletions
from shelf.model import ShelfItem, ShelfState
from shelf.coming_attractions import coming_attractions_note, list_coming_attractions
from shelf.scanner import fetch_recent_completed_downloads, resolve_roots, scan_shelf
from shelf.store import load_state


def _proxy_poster_url(url: str | None) -> str | None:
    if not url:
        return None
    return f"/api/poster?url={quote(url, safe='')}"


def list_items() -> dict:
    """Return the current shelf items for rendering in a UI."""
    state = merge_scan(scan_shelf())
    sorted_items = sorted(
        state.items.values(),
        key=lambda item: (
            item.download_completed_at if item.download_completed_at is not None else item.last_modified
        ),
        reverse=True,
    )
    coming_items = list_coming_attractions(limit=10)
    return {
        "shelf_version": state.version,
        "items": [
            {
                **asdict(item),
                "poster_url": _proxy_poster_url(item.poster_url),
            }
            for item in sorted_items
        ],
        "featured": [
            {
                **item,
                "poster_url": _proxy_poster_url(item.get("poster_url")),
            }
            for item in fetch_recent_completed_downloads(limit=5)
        ],
        "coming_attractions": [
            {
                "title": item.title,
                "path": item.path,
                "kind": item.kind,
                "state": item.state,
            }
            for item in coming_items
        ],
        "coming_attractions_note": coming_attractions_note(coming_items),
    }


def update_status(item_id: str, status: str) -> dict:
    """Update a single item decision and return the updated item."""
    state = load_state()
    state = set_status(state, item_id, status)  # type: ignore[arg-type]
    item = state.items.get(item_id)
    return {"item": asdict(item)} if item else {"item": None}


def apply_deletions_api(dry_run: bool = False) -> dict:
    """Apply deletions for items marked for delete."""
    state = load_state()
    roots = resolve_roots()
    results = apply_deletions(list(state.items.values()), roots, dry_run=dry_run)
    deleted = [result for result in results if result.deleted]
    return {
        "deleted": len(deleted),
        "results": [
            {
                "item_id": result.item.item_id,
                "deleted": result.deleted,
                "error": result.error,
                "external_removed": result.external_removed,
            }
            for result in results
        ],
    }
