"""Utilities for fetching trending media from the Trakt API.

This module provides simple helpers to retrieve trending movies and
television shows from Trakt. It is used as a fallback when MDBList is
unavailable.
"""

from __future__ import annotations

import os
import re
import unicodedata
from typing import Dict, Generator

import requests

TRAKT_BASE_URL = "https://api.trakt.tv"
CLIENT_ID = os.getenv("TRAKT_CLIENT_ID", "")
_WARNED_MISSING_CLIENT_ID = False
HEADERS = {
    "Content-Type": "application/json",
    "trakt-api-key": CLIENT_ID,
    "trakt-api-version": "2",
}


def _get(endpoint: str, params: Dict[str, int] | None = None) -> list[dict]:
    """Internal helper to perform a GET request to the Trakt API."""
    global _WARNED_MISSING_CLIENT_ID
    if not CLIENT_ID:
        if not _WARNED_MISSING_CLIENT_ID:
            print("⚠️ TRAKT_CLIENT_ID not set; Trakt fallback is disabled.")
            _WARNED_MISSING_CLIENT_ID = True
        return []
    try:
        res = requests.get(
            f"{TRAKT_BASE_URL}{endpoint}", headers=HEADERS, params=params, timeout=10
        )
        res.raise_for_status()
        return res.json()
    except requests.RequestException as e:
        print(f"⚠️ Trakt request failed: {e}")
        return []


def _get_user_lists(user: str) -> list[dict]:
    return _get(f"/users/{user}/lists")


def _normalize_list_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    normalized = normalized.replace("\u2019", "'")
    normalized = re.sub(r"[^\w\s]+", " ", normalized.lower())
    return " ".join(normalized.split())


def _get_list_slug_by_name(user: str, name: str) -> str | None:
    normalized = _normalize_list_name(name)
    if not normalized:
        return None
    for lst in _get_user_lists(user):
        title = _normalize_list_name(str(lst.get("name", "")))
        if title == normalized:
            return lst.get("ids", {}).get("slug") or lst.get("slug")
    return None


def get_trending_items(limit: int = 50) -> Generator[dict, None, None]:
    """Yield trending movies and shows from Trakt.

    Args:
        limit: Maximum number of movies and shows to retrieve for each type.

    Yields:
        Dictionary items compatible with MediaRotator's list processing.
    """
    # Trending movies
    for entry in _get("/movies/trending", params={"limit": limit}):
        movie = entry.get("movie", {})
        ids = movie.get("ids", {})
        imdb_id = ids.get("imdb") or ids.get("tmdb")
        if not imdb_id:
            continue
        yield {
            "id": imdb_id,
            "type": "movie",
            "title": movie.get("title"),
            "slug": "trakt-trending-movies",
            "list_title": "Trakt Trending Movies",
        }

    # Trending shows
    for entry in _get("/shows/trending", params={"limit": limit}):
        show = entry.get("show", {})
        ids = show.get("ids", {})
        tvdb_id = ids.get("tvdb") or ids.get("tmdb")
        if not tvdb_id:
            continue
        yield {
            "id": tvdb_id,
            "type": "show",
            "title": show.get("title"),
            "slug": "trakt-trending-shows",
            "list_title": "Trakt Trending Shows",
        }


def get_items_from_trakt_list(
    user: str, slug: str, limit: int | None = None
) -> Generator[dict, None, None]:
    """Yield items from a specific Trakt user list.

    Args:
        user: Trakt username or id that owns the list.
        slug: List identifier (slug).
        limit: Optional limit per request.

    Yields:
        Dictionary items compatible with MediaRotator's list processing.
    """
    endpoint = f"/users/{user}/lists/{slug}/items"
    params = {"limit": limit} if limit else None
    try:
        entries = _get(endpoint, params=params)
    except Exception:
        return

    for entry in entries:
        # Entry may contain a movie or a show under different keys
        if "movie" in entry:
            movie = entry.get("movie", {})
            ids = movie.get("ids", {})
            imdb_id = ids.get("imdb") or ids.get("tmdb")
            if not imdb_id:
                continue
            yield {
                "id": imdb_id,
                "type": "movie",
                "title": movie.get("title"),
                "slug": f"{user}/{slug}",
                "list_title": entry.get("list", {}).get("name") or f"{user}/{slug}",
            }

        elif "show" in entry:
            show = entry.get("show", {})
            ids = show.get("ids", {})
            tvdb_id = ids.get("tvdb") or ids.get("tmdb")
            if not tvdb_id:
                continue
            yield {
                "id": tvdb_id,
                "type": "show",
                "title": show.get("title"),
                "slug": f"{user}/{slug}",
                "list_title": entry.get("list", {}).get("name") or f"{user}/{slug}",
            }


def get_items_from_trakt_list_name(
    user: str, name: str, limit: int | None = None
) -> Generator[dict, None, None]:
    """Yield items from a Trakt list referenced by its display name."""
    slug = _get_list_slug_by_name(user, name)
    if not slug:
        print(f"⚠️ Trakt list not found for user '{user}': '{name}'")
        return
    yield from get_items_from_trakt_list(user, slug, limit=limit)
