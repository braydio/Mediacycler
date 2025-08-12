"""Utilities for fetching trending media from the Trakt API.

This module provides simple helpers to retrieve trending movies and
television shows from Trakt. It is used as a fallback when MDBList is
unavailable.
"""

from __future__ import annotations

import os
from typing import Dict, Generator

import requests

TRAKT_BASE_URL = "https://api.trakt.tv"
CLIENT_ID = os.getenv("TRAKT_CLIENT_ID", "")
HEADERS = {
    "Content-Type": "application/json",
    "trakt-api-key": CLIENT_ID,
    "trakt-api-version": "2",
}


def _get(endpoint: str, params: Dict[str, int] | None = None) -> list[dict]:
    """Internal helper to perform a GET request to the Trakt API."""
    res = requests.get(f"{TRAKT_BASE_URL}{endpoint}", headers=HEADERS, params=params)
    res.raise_for_status()
    return res.json()


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
