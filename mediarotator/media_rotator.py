#!/usr/bin/env python3
"""
MediaRotator CLI - Automated Media Rotation for Radarr/Sonarr

This script manages rotating media by:
1. Fetching lists from MDBList
2. Adding new media to Radarr/Sonarr
3. Removing old media to maintain storage limits
4. Caching processed items to avoid duplicates
"""

import argparse
import os
import sys
from pathlib import Path
import json


# Add the MediaRotator directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# Load environment variables from a local .env if available
if load_dotenv:
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")

from cache import (
    initialize_cache_db,
    add_to_cache,
    is_in_cache,
    remove_from_cache,
    get_oldest_entry,
)
from mdblist_fetcher import get_all_items_from_all_lists
from radarr_handler import lookup_movie, add_movie_to_radarr, delete_movie_by_imdb
from sonarr_handler import lookup_show, add_show_to_sonarr, delete_show_by_tvdb


def _load_rotator_config() -> dict:
    cfg_path = Path(__file__).parent / ".rotator_config.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text())
    except Exception:
        return {}


def _get_dir_size_bytes(path: str) -> int:
    """Return total size in bytes for files under `path`. If path missing, return 0."""
    try:
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
        return total
    except Exception:
        return 0


def check_required_env_vars():
    """Check if required environment variables are set."""
    required_vars = ["RADARR_API_KEY", "SONARR_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("\nPlease set these environment variables:")
        print("export RADARR_API_KEY='your_radarr_api_key'")
        print("export SONARR_API_KEY='your_sonarr_api_key'")
        print("\nOptional variables:")
        print("export RADARR_URL='http://localhost:7878'  # Default shown")
        print("export SONARR_URL='http://localhost:8989'  # Default shown")
        print("export RADARR_QUALITY_PROFILE_ID='1'      # Default shown")
        print("export SONARR_QUALITY_PROFILE_ID='1'      # Default shown")
        print("export SONARR_LANGUAGE_PROFILE_ID='1'     # Default shown")
        print(
            "export ENABLE_NOTIFICATIONS='true'      # Desktop notifications (default: true)"
        )
        print(
            "export MEDIA_CHANGE_FILE='last_media_change.txt'  # Path to change timestamp"
        )
        return False
    return True


def add_new_media(dry_run=False, limit=None):
    """Add new media from MDBList to Radarr/Sonarr."""
    print("🔍 Fetching media from MDBList...")

    added_movies = 0
    added_shows = 0
    processed = 0

    for item in get_all_items_from_all_lists():
        if limit and (added_movies + added_shows) >= limit:
            print(f"✋ Reached limit of {limit} additions")
            break

        processed += 1
        item_id = item.get("id")
        media_type = item.get("type")
        title = item.get("title", "Unknown")
        list_name = item.get("list_title", "Unknown")

        if not item_id:
            print(f"⚠️ Skipping '{title}' - no ID found")
            continue

        # Check if already processed
        print(f"Requested {media_type.title()} '{title}' from SQL MEDIA CACHE (id: {item_id})")
        cached = is_in_cache(item_id)
        if cached:
            # cache check prints a diagnostic; skip processing
            continue

        print(f"\n🎬 Processing {media_type}: {title} (from {list_name})")

        if dry_run:
            print(
                f"[DRY RUN] Would add {media_type} '{title}' (id: {item_id}) to external service and SQL MEDIA CACHE"
            )
            continue

        success = False

        try:
            if media_type == "movie":
                movie_data = lookup_movie(item_id)
                if movie_data:
                    success = add_movie_to_radarr(movie_data)
                    if success:
                        added_movies += 1

            elif media_type == "show":
                show_data = lookup_show(item_id)
                if show_data:
                    success = add_show_to_sonarr(show_data)
                    if success:
                        added_shows += 1

            if success:
                add_to_cache(item_id, media_type, title, list_name)

        except Exception as e:
            print(f"Error processing {title}: {e}")

    print("\n === Summary ===")
    print(f"  Items processed: {processed}")
    print(f"  Movies added: {added_movies}")
    print(f"  Shows added: {added_shows}")
    print(f"  Total added: {added_movies + added_shows}")
    if processed == 0:
        print("⚠️ No items were fetched. Check network connectivity, MDBList availability, or your .rotator_config.json settings.")


def rotate_media(
    dry_run=False,
    movie_limit=50,
    show_limit=25,
    movie_disk_limit_gb: float | None = None,
    show_disk_limit_gb: float | None = None,
    movie_root_path: str | None = None,
    show_root_path: str | None = None,
):
    """Remove oldest media to maintain storage limits."""
    print("🔄 Rotating old media...")

    removed_movies = 0
    removed_shows = 0

    # Remove old movies by count or disk usage
    print(f"\n🎬 Checking movie rotation (count limit: {movie_limit})...")

    # If disk limit provided, use it instead of count limit
    movie_limit_reached = False
    if movie_disk_limit_gb and movie_root_path:
        limit_bytes = int(movie_disk_limit_gb * 1024**3)
        current_size = _get_dir_size_bytes(movie_root_path)
        print(
            f"📦 Current movie storage: {current_size / (1024**3):.2f} GB (limit: {movie_disk_limit_gb} GB)"
        )
        # Remove until under limit
        while current_size > limit_bytes:
            oldest = get_oldest_entry("movie")
            if not oldest:
                print("No movies in cache to rotate")
                break

            movie_id, title = oldest
            print(f"🗑️ Rotating oldest movie: {title}")
            if dry_run:
                print(f"[DRY RUN] Would remove movie: {title}")
                remove_from_cache(movie_id)
                removed_movies += 1
            else:
                if delete_movie_by_imdb(movie_id):
                    remove_from_cache(movie_id)
                    removed_movies += 1
                else:
                    # If deletion failed, remove from cache anyway to prevent stuck state
                    remove_from_cache(movie_id)
                    break

            current_size = _get_dir_size_bytes(movie_root_path)
        movie_limit_reached = True

    if not movie_limit_reached:
        while True:
            oldest = get_oldest_entry("movie")
            if not oldest:
                print("No movies in cache to rotate")
                break

            if removed_movies >= movie_limit:
                print(f"✋ Reached movie rotation limit ({movie_limit})")
                break

            movie_id, title = oldest
            print(f"🗑️ Rotating oldest movie: {title}")

            if dry_run:
                print(f"[DRY RUN] Would remove movie: {title}")
                remove_from_cache(movie_id)
                removed_movies += 1

            if delete_movie_by_imdb(movie_id):
                remove_from_cache(movie_id)
                removed_movies += 1
            else:
                # If deletion failed, remove from cache anyway to prevent stuck state
                remove_from_cache(movie_id)

    # Remove old shows by count or disk usage
    print(f"\n📺 Checking show rotation (count limit: {show_limit})...")
    show_limit_reached = False
    if show_disk_limit_gb and show_root_path:
        limit_bytes = int(show_disk_limit_gb * 1024**3)
        current_size = _get_dir_size_bytes(show_root_path)
        print(
            f"📦 Current show storage: {current_size / (1024**3):.2f} GB (limit: {show_disk_limit_gb} GB)"
        )
        while current_size > limit_bytes:
            oldest = get_oldest_entry("show")
            if not oldest:
                print("No shows in cache to rotate")
                break

            show_id, title = oldest
            print(f"🗑️ Rotating oldest show: {title}")
            if dry_run:
                print(f"[DRY RUN] Would remove show: {title}")
                remove_from_cache(show_id)
                removed_shows += 1
            else:
                if delete_show_by_tvdb(show_id):
                    remove_from_cache(show_id)
                    removed_shows += 1
                else:
                    remove_from_cache(show_id)
                    break

            current_size = _get_dir_size_bytes(show_root_path)
        show_limit_reached = True

    if not show_limit_reached:
        print(f"\n📺 Checking show rotation (limit: {show_limit})...")
        while True:
            oldest = get_oldest_entry("show")
            if not oldest:
                print("No shows in cache to rotate")
                break

            if removed_shows >= show_limit:
                print(f"✋ Reached show rotation limit ({show_limit})")
                break

            show_id, title = oldest
            print(f"🗑️ Rotating oldest show: {title}")

        if dry_run:
            print(f"[DRY RUN] Would remove show: {title}")
            remove_from_cache(show_id)
            removed_shows += 1

        if delete_show_by_tvdb(show_id):
            remove_from_cache(show_id)
            removed_shows += 1
        else:
            # If deletion failed, remove from cache anyway to prevent stuck state
            remove_from_cache(show_id)

    print(f"\n🔄 Rotation Summary:")
    print(f"  Movies rotated: {removed_movies}")
    print(f"  Shows rotated: {removed_shows}")
    print(f"  Total rotated: {removed_movies + removed_shows}")


def main():
    parser = argparse.ArgumentParser(
        description="MediaRotator - Automated Media Management"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--add-limit",
        type=int,
        default=10,
        help="Maximum number of new items to add (default: 10)",
    )
    parser.add_argument(
        "--movie-rotation-limit",
        type=int,
        default=5,
        help="Maximum movies to rotate out (default: 5)",
    )
    parser.add_argument(
        "--show-rotation-limit",
        type=int,
        default=3,
        help="Maximum shows to rotate out (default: 3)",
    )
    parser.add_argument(
        "--add-only", action="store_true", help="Only add new media, skip rotation"
    )
    parser.add_argument(
        "--rotate-only",
        action="store_true",
        help="Only rotate old media, skip adding new",
    )
    parser.add_argument("--version", action="version", version="MediaRotator 1.0.0")

    args = parser.parse_args()

    if args.dry_run:
        print("🧪 DRY RUN MODE - No changes will be made\n")

    # Check environment variables
    if not check_required_env_vars():
        sys.exit(1)

    # Initialize cache database
    initialize_cache_db()
    print("💾 Cache database initialized")
    # Load rotator config (disk limits, roots)
    rotator_cfg = _load_rotator_config()
    movie_root = rotator_cfg.get("movie_root") or os.getenv("MOVIE_ROOT_FOLDER")
    show_root = rotator_cfg.get("show_root") or os.getenv("SHOW_ROOT_FOLDER")
    movie_disk_limit = rotator_cfg.get("movie_disk_limit_gb")
    show_disk_limit = rotator_cfg.get("show_disk_limit_gb")

    try:
        if not args.rotate_only:
            add_new_media(dry_run=args.dry_run, limit=args.add_limit)

        if not args.add_only:
            rotate_media(
                dry_run=args.dry_run,
                movie_limit=args.movie_rotation_limit,
                show_limit=args.show_rotation_limit,
                movie_disk_limit_gb=movie_disk_limit,
                show_disk_limit_gb=show_disk_limit,
                movie_root_path=movie_root,
                show_root_path=show_root,
            )

    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

    print("\n✅ MediaRotator completed successfully!")


if __name__ == "__main__":
    main()
