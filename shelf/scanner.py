from __future__ import annotations

import hashlib
import os
from dataclasses import replace
from datetime import datetime
from typing import Iterable

import requests
from dotenv import load_dotenv

from shelf.model import ShelfItem, ShelfKind


def _hash_id(kind: ShelfKind, path: str) -> str:
    digest = hashlib.sha1(f"{kind}:{path}".encode("utf-8")).hexdigest()
    return digest


def _iter_entries(root: str) -> Iterable[str]:
    if not root or not os.path.isdir(root):
        return []
    entries = []
    try:
        entries = [os.path.join(root, name) for name in os.listdir(root)]
    except OSError:
        return []
    return entries


def _compute_size(path: str) -> int:
    if os.path.islink(path):
        return 0
    if os.path.isfile(path):
        try:
            return os.path.getsize(path)
        except OSError:
            return 0
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            file_path = os.path.join(root, name)
            if os.path.islink(file_path):
                continue
            try:
                total += os.path.getsize(file_path)
            except OSError:
                continue
    return total


def _last_modified(path: str) -> float:
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def _build_items(root: str, kind: ShelfKind) -> list[ShelfItem]:
    items: list[ShelfItem] = []
    for entry in _iter_entries(root):
        if not os.path.exists(entry):
            continue
        title = os.path.basename(entry)
        item_id = _hash_id(kind, entry)
        items.append(
            ShelfItem(
                item_id=item_id,
                title=title,
                path=entry,
                kind=kind,
                size_bytes=_compute_size(entry),
                last_modified=_last_modified(entry),
            )
        )
    return items


def _normalize_path(path: str) -> str:
    return os.path.realpath(path).rstrip(os.sep)


def _append_api_key(url: str, api_key: str | None) -> str:
    if not api_key or "apikey=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}apikey={api_key}"


def _pick_poster(images: list[dict], base_url: str | None = None, api_key: str | None = None) -> str | None:
    if not images:
        return None
    preferred = [img for img in images if img.get("coverType") == "poster"]
    for img in preferred + images:
        remote_url = img.get("remoteUrl")
        if remote_url:
            return remote_url
        url = img.get("url")
        if not url:
            continue
        if base_url and url.startswith("/"):
            return _append_api_key(f"{base_url.rstrip('/')}{url}", api_key)
        return _append_api_key(url, api_key)
    return None


def _fetch_radarr_metadata(api_url: str, api_key: str) -> dict[str, dict]:
    try:
        response = requests.get(
            f"{api_url.rstrip('/')}/api/v3/movie",
            params={"apikey": api_key},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return {}
    metadata: dict[str, dict] = {}
    basename_map: dict[str, dict] = {}
    for movie in data:
        path = movie.get("path")
        poster = _pick_poster(movie.get("images") or [], api_url, api_key)
        genres = movie.get("genres") or []
        if not path:
            continue
        norm = _normalize_path(path)
        metadata[norm] = {"poster_url": poster, "genres": genres}
        base = os.path.basename(norm)
        if base in basename_map:
            basename_map[base] = {}
        else:
            basename_map[base] = {"poster_url": poster, "genres": genres}
    for base, data_item in basename_map.items():
        if data_item:
            metadata[f"__base__:{base}"] = data_item
    return metadata


def _fetch_sonarr_metadata(api_url: str, api_key: str) -> dict[str, dict]:
    try:
        response = requests.get(
            f"{api_url.rstrip('/')}/api/v3/series",
            params={"apikey": api_key},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return {}
    metadata: dict[str, dict] = {}
    basename_map: dict[str, dict] = {}
    for series in data:
        path = series.get("path")
        poster = _pick_poster(series.get("images") or [], api_url, api_key)
        genres = series.get("genres") or []
        if not path:
            continue
        norm = _normalize_path(path)
        metadata[norm] = {"poster_url": poster, "genres": genres}
        base = os.path.basename(norm)
        if base in basename_map:
            basename_map[base] = {}
        else:
            basename_map[base] = {"poster_url": poster, "genres": genres}
    for base, data_item in basename_map.items():
        if data_item:
            metadata[f"__base__:{base}"] = data_item
    return metadata


def _parse_iso_timestamp(value: str | None) -> float | None:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        return float(ts)
    except ValueError:
        return None


def _fetch_recent_radarr_completions(api_url: str, api_key: str, limit: int = 100) -> list[dict]:
    try:
        response = requests.get(
            f"{api_url.rstrip('/')}/api/v3/history",
            params={
                "apikey": api_key,
                "eventType": "downloadFolderImported",
                "sortKey": "date",
                "sortDirection": "descending",
                "pageSize": min(max(limit, 10), 200),
                "page": 1,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return []
    records = data.get("records") or data if isinstance(data, list) else []
    results: list[dict] = []
    for record in records:
        movie = record.get("movie") or {}
        path = movie.get("path")
        if not path:
            continue
        completed_at = _parse_iso_timestamp(record.get("date"))
        if completed_at is None:
            continue
        results.append(
            {
                "kind": "movie",
                "title": movie.get("title", os.path.basename(path)),
                "path": path,
                "poster_url": _pick_poster(movie.get("images") or [], api_url, api_key),
                "completed_at": completed_at,
            }
        )
    return results


def _fetch_recent_sonarr_completions(api_url: str, api_key: str, limit: int = 100) -> list[dict]:
    try:
        response = requests.get(
            f"{api_url.rstrip('/')}/api/v3/history",
            params={
                "apikey": api_key,
                "eventType": "downloadFolderImported",
                "sortKey": "date",
                "sortDirection": "descending",
                "pageSize": min(max(limit, 10), 200),
                "page": 1,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return []
    records = data.get("records") or data if isinstance(data, list) else []
    results: list[dict] = []
    for record in records:
        series = record.get("series") or {}
        path = series.get("path")
        if not path:
            continue
        completed_at = _parse_iso_timestamp(record.get("date"))
        if completed_at is None:
            continue
        results.append(
            {
                "kind": "tv",
                "title": series.get("title", os.path.basename(path)),
                "path": path,
                "poster_url": _pick_poster(series.get("images") or [], api_url, api_key),
                "completed_at": completed_at,
            }
        )
    return results


def fetch_recent_completed_downloads(limit: int = 5) -> list[dict]:
    load_dotenv()
    radarr_url = os.getenv("RADARR_URL")
    radarr_key = os.getenv("RADARR_API_KEY")
    sonarr_url = os.getenv("SONARR_URL")
    sonarr_key = os.getenv("SONARR_API_KEY")

    results: list[dict] = []
    if radarr_url and radarr_key:
        results.extend(_fetch_recent_radarr_completions(radarr_url, radarr_key, limit=200))
    if sonarr_url and sonarr_key:
        results.extend(_fetch_recent_sonarr_completions(sonarr_url, sonarr_key, limit=200))

    results.sort(key=lambda item: item.get("completed_at", 0), reverse=True)
    return results[:limit]


def _build_completion_index(
    radarr_url: str | None,
    radarr_key: str | None,
    sonarr_url: str | None,
    sonarr_key: str | None,
) -> tuple[dict[str, float], dict[str, float]]:
    exact: dict[str, float] = {}
    by_basename: dict[str, float] = {}

    completions: list[dict] = []
    if radarr_url and radarr_key:
        completions.extend(_fetch_recent_radarr_completions(radarr_url, radarr_key, limit=200))
    if sonarr_url and sonarr_key:
        completions.extend(_fetch_recent_sonarr_completions(sonarr_url, sonarr_key, limit=200))

    for item in completions:
        path = item.get("path")
        completed_at = item.get("completed_at")
        kind = item.get("kind")
        if not isinstance(path, str) or not isinstance(completed_at, (int, float)) or not kind:
            continue
        norm = _normalize_path(path)
        key_exact = f"{kind}:{norm}"
        existing = exact.get(key_exact)
        if existing is None or completed_at > existing:
            exact[key_exact] = float(completed_at)

        base = os.path.basename(norm)
        key_base = f"{kind}:{base}"
        existing_base = by_basename.get(key_base)
        if existing_base is None or completed_at > existing_base:
            by_basename[key_base] = float(completed_at)

    return exact, by_basename


def _attach_posters(items: list[ShelfItem]) -> list[ShelfItem]:
    load_dotenv()
    radarr_url = os.getenv("RADARR_URL")
    radarr_key = os.getenv("RADARR_API_KEY")
    sonarr_url = os.getenv("SONARR_URL")
    sonarr_key = os.getenv("SONARR_API_KEY")

    movie_meta: dict[str, dict] = {}
    tv_meta: dict[str, dict] = {}

    if radarr_url and radarr_key:
        movie_meta = _fetch_radarr_metadata(radarr_url, radarr_key)
    if sonarr_url and sonarr_key:
        tv_meta = _fetch_sonarr_metadata(sonarr_url, sonarr_key)

    completion_exact, completion_base = _build_completion_index(
        radarr_url=radarr_url,
        radarr_key=radarr_key,
        sonarr_url=sonarr_url,
        sonarr_key=sonarr_key,
    )

    enriched: list[ShelfItem] = []
    for item in items:
        norm = _normalize_path(item.path)
        base = os.path.basename(norm)
        if item.kind == "movie":
            data_item = movie_meta.get(norm) or movie_meta.get(f"__base__:{base}") or {}
            kind_key = "movie"
        else:
            data_item = tv_meta.get(norm) or tv_meta.get(f"__base__:{base}") or {}
            kind_key = "tv"

        completed_at = completion_exact.get(f"{kind_key}:{norm}") or completion_base.get(f"{kind_key}:{base}")
        enriched.append(
            replace(
                item,
                poster_url=data_item.get("poster_url"),
                genres=list(data_item.get("genres") or []),
                download_completed_at=float(completed_at) if completed_at is not None else None,
            )
        )
    return enriched


def resolve_paths() -> tuple[str, str]:
    load_dotenv()
    movies = (
        os.getenv("SHELF_MOVIES_PATH")
        or os.getenv("SEEDBOX_MOVIES_DEST")
        or os.getenv("ROTATING_MOVIES_PATH")
        or ""
    )
    tv = (
        os.getenv("SHELF_TV_PATH")
        or os.getenv("SEEDBOX_TV_DEST")
        or os.getenv("ROTATING_TV_PATH")
        or ""
    )
    return movies, tv


def scan_shelf() -> list[ShelfItem]:
    movies_root, tv_root = resolve_paths()
    items = []
    if movies_root:
        items.extend(_build_items(movies_root, "movie"))
    if tv_root:
        items.extend(_build_items(tv_root, "tv"))
    return _attach_posters(items)


def resolve_roots() -> list[str]:
    movies_root, tv_root = resolve_paths()
    roots = [root for root in [movies_root, tv_root] if root]
    return roots


def refresh_metadata(item: ShelfItem) -> ShelfItem:
    if not os.path.exists(item.path):
        return item
    return replace(
        item,
        size_bytes=_compute_size(item.path),
        last_modified=_last_modified(item.path),
    )
