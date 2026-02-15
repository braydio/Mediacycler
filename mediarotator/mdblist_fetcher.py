"""Fetch curated lists from MDBList with Trakt fallback.

This module retrieves movie and show identifiers from MDBList. If the
service is unavailable, it falls back to pulling trending items from the
Trakt API.
"""

import json
import re
import unicodedata
from pathlib import Path

import requests

from prefs_loader import get_trakt_user, load_list_prefs
from trakt_fetcher import (
    get_items_from_trakt_list,
    get_items_from_trakt_list_name,
    get_trending_items,
)

MDBLIST_BASE_URL = "https://mdblist.com/api"
DEFAULT_MDBLIST_USER = "hd-movie-lists"


def _load_config() -> dict:
    cfg_path = Path(__file__).parent / ".rotator_config.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text())
    except Exception:
        return {}


def _fetch_mdblist_user_lists(user: str) -> list[dict]:
    res = requests.get(f"{MDBLIST_BASE_URL}/user/{user}", timeout=10)
    res.raise_for_status()
    return res.json().get("lists", [])


def _normalize_list_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    normalized = normalized.replace("\u2019", "'")
    normalized = re.sub(r"[^\w\s]+", " ", normalized.lower())
    return " ".join(normalized.split())


def _iter_mdblist_list_items(user: str, slug: str, title: str, expected_type: str | None = None):
    res = requests.get(f"{MDBLIST_BASE_URL}/?list={user}/{slug}", timeout=10)
    res.raise_for_status()
    items = res.json().get("items", [])
    for item in items:
        media_type = "movie" if item.get("type") == "movie" else "show"
        if expected_type and media_type != expected_type:
            continue
        yield {
            "id": item.get("imdb_id") or item.get("tvdb_id"),
            "type": media_type,
            "title": item.get("title"),
            "slug": slug,
            "list_title": title,
        }


def get_all_items_from_all_lists():
    """Yield items for the rotator.

    Behavior:
    - If `.rotator_config.json` sets `use_mdblist: true`, fetch MDBList lists.
    - If `UserPrefs_Lists.yaml` exists and `use_mdblist` is not set, prefer MDBList.
    - Otherwise prefer Trakt lists provided in config (`movie_lists`/`show_lists`) or
      default to Trakt trending items.
    """
    config = _load_config()
    base_dir = Path(__file__).parent
    list_prefs = load_list_prefs(base_dir)
    has_list_prefs = any(
        list_prefs[key][tier]
        for key in ("movies", "tv")
        for tier in ("primary", "spice")
    )

    use_mdblist = config.get("use_mdblist")
    if use_mdblist is None:
        use_mdblist = has_list_prefs

    if use_mdblist:
        mdblist_user = config.get("mdblist_user", DEFAULT_MDBLIST_USER)
        try:
            lists = _fetch_mdblist_user_lists(mdblist_user)
        except requests.RequestException as e:
            print(f"⚠️ MDBList unavailable or slow: {e}")
            print("➡️ Falling back to Trakt trending items")
            yield from get_trending_items()
            return

        list_map = {
            _normalize_list_title(lst.get("title", "")): lst for lst in lists
        }
        movie_titles = list_prefs["movies"]["primary"] + list_prefs["movies"]["spice"]
        show_titles = list_prefs["tv"]["primary"] + list_prefs["tv"]["spice"]

        if not movie_titles and not show_titles:
            for lst in lists:
                slug = lst.get("slug")
                title = lst.get("title")
                if not slug or not title:
                    continue
                try:
                    yield from _iter_mdblist_list_items(mdblist_user, slug, title)
                except requests.RequestException as e:
                    print(f"⚠️ Failed to fetch list '{title}': {e}")
            return

        def _iter_titles(titles: list[str], expected_type: str):
            seen = set()
            for title in titles:
                key = _normalize_list_title(title)
                if not key or key in seen:
                    continue
                seen.add(key)
                lst = list_map.get(key)
                if not lst:
                    print(f"⚠️ MDBList list not found: '{title}'")
                    continue
                slug = lst.get("slug")
                list_title = lst.get("title") or title
                if not slug:
                    continue
                try:
                    yield from _iter_mdblist_list_items(
                        mdblist_user, slug, list_title, expected_type=expected_type
                    )
                except requests.RequestException as e:
                    print(f"⚠️ Failed to fetch list '{list_title}': {e}")

        yield from _iter_titles(movie_titles, expected_type="movie")
        yield from _iter_titles(show_titles, expected_type="show")
        return

    # Prefer Trakt lists
    trakt_user = config.get("trakt_user") or get_trakt_user(base_dir)
    movie_lists = config.get("movie_lists")
    show_lists = config.get("show_lists")

    if not movie_lists and not show_lists and has_list_prefs:
        movie_lists = list_prefs["movies"]["primary"] + list_prefs["movies"]["spice"]
        show_lists = list_prefs["tv"]["primary"] + list_prefs["tv"]["spice"]

    if not movie_lists:
        movie_lists = ["trending"]
    if not show_lists:
        show_lists = ["trending"]

    def _iter_list_spec(spec, expected_type=None):
        if spec == "trending":
            for item in get_trending_items():
                if expected_type and item.get("type") != expected_type:
                    continue
                yield item
            return

        if "/" in spec:
            user, slug = spec.split("/", 1)
            for item in get_items_from_trakt_list(user, slug):
                if expected_type and item.get("type") != expected_type:
                    continue
                yield item
            return

        if trakt_user:
            for item in get_items_from_trakt_list_name(trakt_user, spec):
                if expected_type and item.get("type") != expected_type:
                    continue
                yield item
            return

        print(f"⚠️ Trakt list '{spec}' skipped (no trakt user configured)")

    for spec in movie_lists:
        yield from _iter_list_spec(spec, expected_type="movie")

    for spec in show_lists:
        yield from _iter_list_spec(spec, expected_type="show")
