"""Fetch curated lists from MDBList with Trakt fallback.

This module retrieves movie and show identifiers from MDBList. If the
service is unavailable, it falls back to pulling trending items from the
Trakt API.
"""

import json
from pathlib import Path

import requests

from trakt_fetcher import get_trending_items, get_items_from_trakt_list

MDBLIST_BASE_URL = "https://mdblist.com/api"
USER = "hd-movie-lists"


def _load_config() -> dict:
    cfg_path = Path(__file__).parent / ".rotator_config.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text())
    except Exception:
        return {}


def get_all_items_from_all_lists():
    """Yield items for the rotator.

    Behavior:
    - If `.rotator_config.json` exists and sets `use_mdblist: true`, fetch MDBList lists.
    - Otherwise prefer Trakt lists provided in config (`movie_lists`/`show_lists`) or
      default to Trakt trending items.
    """
    config = _load_config()

    if config.get("use_mdblist"):
        # Original MDBList behavior
        try:
            res = requests.get(f"{MDBLIST_BASE_URL}/user/{USER}", timeout=10)
            res.raise_for_status()
            lists = res.json()["lists"]
        except requests.RequestException as e:
            print(f"⚠️ MDBList unavailable or slow: {e}")
            print("➡️ Falling back to Trakt trending items")
            yield from get_trending_items()
            return

        for lst in lists:
            slug = lst["slug"]
            title = lst["title"]
            try:
                res = requests.get(f"{MDBLIST_BASE_URL}/?list={USER}/{slug}", timeout=10)
                res.raise_for_status()
                items = res.json()["items"]
                for item in items:
                    yield {
                        "id": item.get("imdb_id") or item.get("tvdb_id"),
                        "type": "movie" if item.get("type") == "movie" else "show",
                        "title": item.get("title"),
                        "slug": slug,
                        "list_title": title,
                    }
            except requests.RequestException as e:
                print(f"⚠️ Failed to fetch list '{title}': {e}")
        return

    # Prefer Trakt lists
    movie_lists = config.get("movie_lists", ["trending"])
    show_lists = config.get("show_lists", ["trending"])

    # Helper to iterate a trakt list spec
    def _iter_list_spec(spec, expected_type=None):
        # 'trending' is a special keyword
        if spec == "trending":
            for item in get_trending_items():
                if expected_type and item.get("type") != expected_type:
                    continue
                yield item
            return

        # otherwise expect 'user/slug'
        if "/" in spec:
            user, slug = spec.split("/", 1)
            for item in get_items_from_trakt_list(user, slug):
                if expected_type and item.get("type") != expected_type:
                    continue
                yield item

    # Yield configured movie lists
    for spec in movie_lists:
        yield from _iter_list_spec(spec, expected_type="movie")

    # Yield configured show lists
    for spec in show_lists:
        yield from _iter_list_spec(spec, expected_type="show")
