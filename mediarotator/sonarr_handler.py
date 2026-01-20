"""Helpers for interacting with the Sonarr API."""

import os
from pathlib import Path
import requests

from notifications import notify_change

def _in_docker() -> bool:
    if Path("/.dockerenv").exists():
        return True
    try:
        return "docker" in Path("/proc/1/cgroup").read_text()
    except Exception:
        return False


def _default_service_url(port: int) -> str:
    if _in_docker():
        return f"http://host.docker.internal:{port}"
    return f"http://localhost:{port}"


SONARR_API_KEY = os.getenv("SONARR_API_KEY")
SONARR_URL = os.getenv("SONARR_URL", _default_service_url(8989))
# Root folder used when adding new shows. Configure via env or rotator config.
SHOW_ROOT_FOLDER = os.getenv("SHOW_ROOT_FOLDER", "/mnt/netstorage/Media/RotatingTV")
QUALITY_PROFILE_ID = int(os.getenv("SONARR_QUALITY_PROFILE_ID", "1"))  # default profile
LANGUAGE_PROFILE_ID = int(os.getenv("SONARR_LANGUAGE_PROFILE_ID", "1"))  # default

HEADERS = {"X-Api-Key": SONARR_API_KEY}


def lookup_show(tvdb_id):
    """Look up show details by TVDB ID."""
    res = requests.get(
        f"{SONARR_URL}/api/v3/series/lookup?term=tvdb:{tvdb_id}", headers=HEADERS
    )
    res.raise_for_status()
    results = res.json()
    return results[0] if results else None


def add_show_to_sonarr(show_data):
    """Add a show to Sonarr and trigger a search."""
    # Verify the configured root folder exists in Sonarr
    try:
        res = requests.get(f"{SONARR_URL}/api/v3/rootfolder", headers=HEADERS)
        res.raise_for_status()
        root_paths = [r.get("path") for r in res.json()]
    except Exception:
        root_paths = []

    if SHOW_ROOT_FOLDER not in root_paths:
        print(f"❌ Configured root folder '{SHOW_ROOT_FOLDER}' is not known to Sonarr")
        print("Ensure the folder exists on the Sonarr host and is added as a root folder in Sonarr settings.")
        return False

    payload = {
        "title": show_data["title"],
        "qualityProfileId": QUALITY_PROFILE_ID,
        "languageProfileId": LANGUAGE_PROFILE_ID,
        "tvdbId": show_data["tvdbId"],
        "titleSlug": show_data["titleSlug"],
        "images": show_data.get("images", []),
        "seasons": show_data.get("seasons", []),
        "monitored": True,
        "seasonFolder": True,
        "rootFolderPath": SHOW_ROOT_FOLDER,
        "addOptions": {"searchForMissingEpisodes": True},
    }
    res = requests.post(f"{SONARR_URL}/api/v3/series", headers=HEADERS, json=payload)
    if res.status_code == 201:
        print(f"Added show: {show_data['title']}")
        notify_change(f"Added show: {show_data['title']}")
        return True
    elif res.status_code == 400 and "already exists" in res.text.lower():
        print(f"Show already exists in Sonarr: {show_data['title']}")
        return False
    else:
        print(f"Failed to add show: {res.status_code} - {res.text}")
        return False


def delete_show_by_tvdb(tvdb_id, delete_files=True):
    """Remove a show by TVDB ID."""
    res = requests.get(f"{SONARR_URL}/api/v3/series", headers=HEADERS)
    res.raise_for_status()
    series = res.json()
    for show in series:
        if show.get("tvdbId") == tvdb_id:
            show_id = show["id"]
            delete_payload = {"deleteFiles": delete_files, "addImportExclusion": True}
            del_res = requests.delete(
                f"{SONARR_URL}/api/v3/series/{show_id}",
                headers=HEADERS,
                json=delete_payload,
            )
            if del_res.status_code == 200:
                print(f"🗑️ Deleted show: {show['title']}")
                notify_change(f"Deleted show: {show['title']}")
                return True
    print(f"No matching show found to delete with TVDB ID {tvdb_id}")
    return False
