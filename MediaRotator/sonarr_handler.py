"""Helpers for interacting with the Sonarr API."""

import os
import requests

from notifications import notify_change

SONARR_API_KEY = os.getenv("SONARR_API_KEY")
SONARR_URL = os.getenv("SONARR_URL", "http://localhost:8989")
SHOW_ROOT_FOLDER = "/mnt/netstorage/Media/RotatingTV"
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
