from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

from shelf.model import ShelfItem


@dataclass
class DeletionResult:
    item: ShelfItem
    deleted: bool
    error: str | None = None
    external_removed: bool = False


def _is_safe(path: str, roots: list[str]) -> bool:
    real_path = os.path.realpath(path)
    for root in roots:
        real_root = os.path.realpath(root)
        if real_path == real_root or real_path.startswith(real_root + os.sep):
            return True
    return False


def _delete_path(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)


def _normalize_path(path: str) -> str:
    return os.path.realpath(path).rstrip(os.sep)


def _remove_from_qbittorrent(item: ShelfItem) -> bool:
    load_dotenv()
    base_url = os.getenv("QBITTORRENT_URL")
    username = os.getenv("QBITTORRENT_USERNAME")
    password = os.getenv("QBITTORRENT_PASSWORD")
    if not base_url or not username or not password:
        return False

    basename = os.path.basename(item.path).lower()
    full_path = _normalize_path(item.path).lower()
    session = requests.Session()
    try:
        login = session.post(
            f"{base_url.rstrip('/')}/api/v2/auth/login",
            data={"username": username, "password": password},
            timeout=8,
        )
        if login.status_code != 200 or "Ok." not in login.text:
            return False

        info = session.get(f"{base_url.rstrip('/')}/api/v2/torrents/info", timeout=8)
        info.raise_for_status()
        torrents = info.json()
        hashes: list[str] = []
        for torrent in torrents:
            hash_value = torrent.get("hash")
            if not hash_value:
                continue
            name = str(torrent.get("name") or "").lower()
            content_path = str(torrent.get("content_path") or "").lower()
            save_path = str(torrent.get("save_path") or "").lower()
            if basename and basename in name:
                hashes.append(hash_value)
                continue
            if full_path and (full_path in content_path or full_path in save_path):
                hashes.append(hash_value)

        if not hashes:
            return False

        delete = session.post(
            f"{base_url.rstrip('/')}/api/v2/torrents/delete",
            data={"hashes": "|".join(sorted(set(hashes))), "deleteFiles": "true"},
            timeout=8,
        )
        return delete.status_code == 200
    except requests.RequestException:
        return False


def _remove_from_radarr(item: ShelfItem) -> bool:
    load_dotenv()
    api_url = os.getenv("RADARR_URL")
    api_key = os.getenv("RADARR_API_KEY")
    if not api_url or not api_key:
        return False
    target = _normalize_path(item.path)
    target_base = os.path.basename(target)
    try:
        response = requests.get(
            f"{api_url.rstrip('/')}/api/v3/movie",
            params={"apikey": api_key},
            timeout=10,
        )
        response.raise_for_status()
        for movie in response.json():
            path = movie.get("path")
            movie_id = movie.get("id")
            if not path or movie_id is None:
                continue
            movie_path = _normalize_path(path)
            if movie_path != target and os.path.basename(movie_path) != target_base:
                continue
            delete = requests.delete(
                f"{api_url.rstrip('/')}/api/v3/movie/{movie_id}",
                params={"apikey": api_key},
                json={"deleteFiles": True, "addImportExclusion": True},
                timeout=10,
            )
            return delete.status_code in (200, 202)
    except requests.RequestException:
        return False
    return False


def _remove_from_sonarr(item: ShelfItem) -> bool:
    load_dotenv()
    api_url = os.getenv("SONARR_URL")
    api_key = os.getenv("SONARR_API_KEY")
    if not api_url or not api_key:
        return False
    target = _normalize_path(item.path)
    target_base = os.path.basename(target)
    try:
        response = requests.get(
            f"{api_url.rstrip('/')}/api/v3/series",
            params={"apikey": api_key},
            timeout=10,
        )
        response.raise_for_status()
        for series in response.json():
            path = series.get("path")
            series_id = series.get("id")
            if not path or series_id is None:
                continue
            series_path = _normalize_path(path)
            if series_path != target and os.path.basename(series_path) != target_base:
                continue
            delete = requests.delete(
                f"{api_url.rstrip('/')}/api/v3/series/{series_id}",
                params={"apikey": api_key},
                json={"deleteFiles": True, "addImportExclusion": True},
                timeout=10,
            )
            return delete.status_code in (200, 202)
    except requests.RequestException:
        return False
    return False


def _remove_from_external_services(item: ShelfItem) -> bool:
    removed = _remove_from_qbittorrent(item)
    if item.kind == "movie":
        removed = _remove_from_radarr(item) or removed
    else:
        removed = _remove_from_sonarr(item) or removed
    return removed


def apply_deletions(items: list[ShelfItem], roots: list[str], dry_run: bool = False) -> list[DeletionResult]:
    results: list[DeletionResult] = []
    for item in items:
        if item.status != "delete":
            continue

        if dry_run:
            results.append(DeletionResult(item=item, deleted=True, external_removed=False))
            continue

        external_removed = _remove_from_external_services(item)

        if not os.path.exists(item.path):
            results.append(
                DeletionResult(
                    item=item,
                    deleted=external_removed,
                    error=None if external_removed else "missing",
                    external_removed=external_removed,
                )
            )
            continue
        if not _is_safe(item.path, roots):
            results.append(
                DeletionResult(
                    item=item,
                    deleted=False,
                    error="unsafe path",
                    external_removed=external_removed,
                )
            )
            continue
        try:
            _delete_path(item.path)
            results.append(DeletionResult(item=item, deleted=True, external_removed=external_removed))
        except OSError as exc:
            results.append(
                DeletionResult(
                    item=item,
                    deleted=False,
                    error=str(exc),
                    external_removed=external_removed,
                )
            )
    return results
