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
import json
import os
import re
import shlex
import subprocess
import sys
import shutil
from pathlib import Path
from dataclasses import dataclass


# Add the MediaRotator directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

def _load_env_fallback(env_path: Path) -> None:
    if not env_path.exists():
        return
    try:
        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")  # basic quote handling
            if key:
                os.environ.setdefault(key, value)
    except Exception:
        return


try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

# Load environment variables from a local .env if available
env_path = Path(__file__).parent / ".env"
if load_dotenv:
    load_dotenv(dotenv_path=env_path)
else:
    _load_env_fallback(env_path)

from cache import (
    initialize_cache_db,
    add_to_cache,
    is_in_cache,
    remove_from_cache,
    get_oldest_entry,
)
from mdblist_fetcher import get_all_items_from_all_lists
from prefs_loader import load_user_prefs
from radarr_handler import lookup_movie, add_movie_to_radarr, delete_movie_by_imdb
from sonarr_handler import lookup_show, add_show_to_sonarr, delete_show_by_tvdb


@dataclass
class DuplicatePruneResult:
    removed_movies: int = 0
    removed_shows: int = 0
    removed_paths: list[str] | None = None


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
    if os.getenv("ROTATOR_DIR_SIZE_METHOD", "").lower() == "du":
        try:
            result = subprocess.check_output(["du", "-sb", path]).decode().split()[0]
            return int(result)
        except Exception:
            pass
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


def check_required_env_vars(require_api: bool = True):
    """Check if required environment variables are set."""
    if not require_api:
        return True
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


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _coalesce(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _build_ssh_command(port: int, key_path: str | None, strict: str | None, extra_args: str | None):
    cmd = ["ssh", "-p", str(port)]
    if key_path:
        cmd.extend(["-i", key_path])
    if strict:
        cmd.extend(["-o", f"StrictHostKeyChecking={strict}"])
    if extra_args:
        cmd.extend(shlex.split(extra_args))
    return cmd


def _normalize_media_name(name: str) -> str:
    base = name.strip().lower()
    # Strip common resolution/source noise from folder names.
    base = re.sub(r"\b(2160p|1080p|720p|480p|x264|x265|h\.?264|h\.?265|hevc|web[- ]?dl|bluray|brrip)\b", "", base)
    base = re.sub(r"[^a-z0-9]+", "", base)
    return base


def _is_within(path: str, root: str) -> bool:
    norm_path = os.path.realpath(path)
    norm_root = os.path.realpath(root)
    return norm_path == norm_root or norm_path.startswith(norm_root + os.sep)


def _list_library_entries(root: str | None) -> dict[str, str]:
    if not root or not os.path.isdir(root):
        return {}
    entries: dict[str, str] = {}
    try:
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if not os.path.exists(path):
                continue
            key = _normalize_media_name(name)
            if key:
                entries[key] = path
    except OSError:
        return {}
    return entries


def _delete_local_path(path: str, safe_root: str, dry_run: bool) -> bool:
    if not os.path.exists(path):
        return False
    if not _is_within(path, safe_root):
        print(f"⚠️ Refusing to delete path outside rotating root: {path}")
        return False
    if dry_run:
        print(f"[DRY RUN] Would delete duplicate rotating path: {path}")
        return True
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return True
    except OSError as exc:
        print(f"⚠️ Failed to delete duplicate path {path}: {exc}")
        return False


def _prune_rotating_duplicates(
    movie_root: str | None,
    show_root: str | None,
    movie_library_root: str | None,
    show_library_root: str | None,
    dry_run: bool = False,
) -> DuplicatePruneResult:
    """
    Remove items from rotating libraries if matching names already exist
    in permanent libraries.
    """
    result = DuplicatePruneResult(removed_paths=[])

    movie_library = _list_library_entries(movie_library_root)
    movie_rotating = _list_library_entries(movie_root)
    for key, rotate_path in movie_rotating.items():
        if key not in movie_library:
            continue
        print(
            f"🧹 Duplicate movie detected in rotating library: "
            f"{rotate_path} (exists in {movie_library[key]})"
        )
        if movie_root and _delete_local_path(rotate_path, movie_root, dry_run):
            result.removed_movies += 1
            result.removed_paths.append(rotate_path)

    show_library = _list_library_entries(show_library_root)
    show_rotating = _list_library_entries(show_root)
    for key, rotate_path in show_rotating.items():
        if key not in show_library:
            continue
        print(
            f"🧹 Duplicate show detected in rotating library: "
            f"{rotate_path} (exists in {show_library[key]})"
        )
        if show_root and _delete_local_path(rotate_path, show_root, dry_run):
            result.removed_shows += 1
            result.removed_paths.append(rotate_path)

    return result


def _sync_seedbox_media(
    rotator_cfg: dict,
    movie_root: str | None,
    show_root: str | None,
    dry_run: bool = False,
):
    seedbox_cfg = rotator_cfg.get("seedbox", {}) if isinstance(rotator_cfg, dict) else {}

    enabled = _parse_bool(
        _coalesce(seedbox_cfg.get("enabled"), os.getenv("SEEDBOX_SYNC_ENABLED")),
        default=False,
    )
    if not enabled:
        print("ℹ️ Seedbox sync disabled")
        return

    host = _coalesce(seedbox_cfg.get("host"), os.getenv("SEEDBOX_HOST"))
    user = _coalesce(seedbox_cfg.get("user"), os.getenv("SEEDBOX_USER"))
    if not host or not user:
        print("⚠️ Seedbox sync enabled but SEEDBOX_HOST/SEEDBOX_USER are not set")
        return

    port = int(_coalesce(seedbox_cfg.get("port"), os.getenv("SEEDBOX_PORT"), 22))
    movies_src = _coalesce(
        seedbox_cfg.get("movies_path"),
        os.getenv("SEEDBOX_MOVIES_PATH"),
        "~/media/movies",
    )
    tv_src = _coalesce(
        seedbox_cfg.get("tv_path"),
        os.getenv("SEEDBOX_TV_PATH"),
        "~/media/tv",
    )
    movies_dest = _coalesce(
        seedbox_cfg.get("movies_dest"),
        os.getenv("SEEDBOX_MOVIES_DEST"),
        movie_root,
    )
    tv_dest = _coalesce(
        seedbox_cfg.get("tv_dest"),
        os.getenv("SEEDBOX_TV_DEST"),
        show_root,
    )
    cleanup_hours = _coalesce(
        seedbox_cfg.get("cleanup_delay_hours"),
        os.getenv("SEEDBOX_CLEANUP_DELAY_HOURS"),
        12,
    )
    key_path = _coalesce(seedbox_cfg.get("ssh_key_path"), os.getenv("SEEDBOX_SSH_KEY_PATH"))
    strict = _coalesce(
        seedbox_cfg.get("ssh_strict_host_key_checking"),
        os.getenv("SEEDBOX_SSH_STRICT_HOST_KEY_CHECKING"),
        "accept-new",
    )
    extra_args = _coalesce(seedbox_cfg.get("ssh_extra_args"), os.getenv("SEEDBOX_SSH_EXTRA_ARGS"))

    ssh_cmd = _build_ssh_command(port, key_path, strict, extra_args)
    ssh_cmd_str = " ".join(shlex.quote(part) for part in ssh_cmd)

    def _rsync_one(label: str, src_path: str | None, dest_path: str | None):
        if not src_path or not dest_path:
            print(f"⚠️ Seedbox sync skipped for {label}: missing source/destination paths")
            return False
        if not dry_run:
            os.makedirs(dest_path, exist_ok=True)

        src = f"{user}@{host}:{src_path.rstrip('/')}/"
        dest = dest_path.rstrip("/") + "/"
        cmd = ["rsync", "-a", "--partial", "-e", ssh_cmd_str]
        if dry_run:
            cmd.append("--dry-run")
        cmd.extend([src, dest])

        print(f"📥 Syncing {label} from seedbox: {src_path} -> {dest_path}")
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            print(f"⚠️ Seedbox sync failed for {label} (exit {result.returncode})")
            return False
        return True

    def _cleanup_one(label: str, src_path: str | None, delay_hours: float | int | None):
        if not src_path or delay_hours is None:
            return
        try:
            minutes = int(float(delay_hours) * 60)
        except (TypeError, ValueError):
            print(f"⚠️ Invalid cleanup delay for {label}: {delay_hours}")
            return
        if minutes < 0:
            print(f"ℹ️ Cleanup disabled for {label} (negative delay)")
            return

        quoted_path = shlex.quote(src_path)
        delete_files = (
            f"find {quoted_path} -mindepth 1 -type f -mmin +{minutes} -print0 | "
            "xargs -0 -r rm -f"
        )
        delete_dirs = f"find {quoted_path} -type d -empty -delete"
        remote_cmd = f"{delete_files}; {delete_dirs}"

        print(f"🧹 Cleaning up seedbox {label} (older than {minutes} minutes)")
        if dry_run:
            print(f"[DRY RUN] Would run: {remote_cmd}")
            return
        # Run cleanup on the remote seedbox host.
        subprocess.run(ssh_cmd + [f"{user}@{host}", "bash", "-lc", remote_cmd], check=False)

    movies_synced = _rsync_one("movies", movies_src, movies_dest)
    tv_synced = _rsync_one("tv", tv_src, tv_dest)

    if movies_synced:
        _cleanup_one("movies", movies_src, cleanup_hours)
    if tv_synced:
        _cleanup_one("tv", tv_src, cleanup_hours)


def add_new_media(dry_run=False, limit=None, movie_limit=None, show_limit=None):
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

        if media_type == "movie" and movie_limit is not None and added_movies >= movie_limit:
            continue
        if media_type == "show" and show_limit is not None and added_shows >= show_limit:
            continue

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
                continue

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
                continue

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
    parser.add_argument(
        "--sync-only",
        action="store_true",
        help="Only sync seedbox media, skip adding and rotation",
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip seedbox sync even if enabled",
    )
    parser.add_argument("--version", action="version", version="MediaRotator 1.0.0")

    args = parser.parse_args()

    if args.dry_run:
        print("🧪 DRY RUN MODE - No changes will be made\n")

    # Load rotator config (disk limits, roots)
    rotator_cfg = _load_rotator_config()
    user_prefs = load_user_prefs(Path(__file__).parent)
    movie_root = (
        rotator_cfg.get("movie_root")
        or user_prefs.get("paths", {}).get("jellyfin", {}).get("movies")
        or os.getenv("MOVIE_ROOT_FOLDER")
    )
    show_root = (
        rotator_cfg.get("show_root")
        or user_prefs.get("paths", {}).get("jellyfin", {}).get("tv")
        or os.getenv("SHOW_ROOT_FOLDER")
    )
    movie_disk_limit = rotator_cfg.get("movie_disk_limit_gb")
    show_disk_limit = rotator_cfg.get("show_disk_limit_gb")
    movie_library_root = (
        rotator_cfg.get("movie_library_root")
        or os.getenv("MOVIES_LIBRARY_PATH")
        or "/mnt/netstorage/Media/Movies"
    )
    show_library_root = (
        rotator_cfg.get("show_library_root")
        or os.getenv("TV_LIBRARY_PATH")
        or "/mnt/netstorage/Media/TV"
    )
    if movie_disk_limit is None:
        max_tb = user_prefs.get("storage_limits", {}).get("movies", {}).get("max_size_tb")
        if isinstance(max_tb, (int, float)):
            movie_disk_limit = float(max_tb) * 1024
    if show_disk_limit is None:
        max_tb = user_prefs.get("storage_limits", {}).get("tv", {}).get("max_size_tb")
        if isinstance(max_tb, (int, float)):
            show_disk_limit = float(max_tb) * 1024

    cadence = user_prefs.get("rotation_engine", {}).get("cadence", {})
    per_run = cadence.get("max_additions_per_run", {}) if isinstance(cadence, dict) else {}
    movie_add_limit = per_run.get("movies") if isinstance(per_run, dict) else None
    show_add_limit = per_run.get("tv") if isinstance(per_run, dict) else None

    do_add = not args.rotate_only and not args.sync_only
    do_rotate = not args.add_only and not args.sync_only
    do_sync = not args.skip_sync

    # Check environment variables
    if not check_required_env_vars(require_api=do_add or do_rotate):
        sys.exit(1)

    # Initialize cache database for add/rotate flows
    if do_add or do_rotate:
        initialize_cache_db()
        print("💾 Cache database initialized")

    try:
        if do_add:
            add_new_media(
                dry_run=args.dry_run,
                limit=args.add_limit,
                movie_limit=movie_add_limit,
                show_limit=show_add_limit,
            )

        if do_sync:
            _sync_seedbox_media(
                rotator_cfg=rotator_cfg,
                movie_root=movie_root,
                show_root=show_root,
                dry_run=args.dry_run,
            )

        if do_sync or do_rotate:
            print("\n🧭 Checking rotating libraries for duplicates in permanent libraries...")
            print(f"  Rotating movie root: {movie_root}")
            print(f"  Rotating show root: {show_root}")
            print(f"  Permanent movie root: {movie_library_root}")
            print(f"  Permanent show root: {show_library_root}")
            prune = _prune_rotating_duplicates(
                movie_root=movie_root,
                show_root=show_root,
                movie_library_root=movie_library_root,
                show_library_root=show_library_root,
                dry_run=args.dry_run,
            )
            print(
                f"🧹 Duplicate prune summary: "
                f"{prune.removed_movies} movie(s), {prune.removed_shows} show(s) removed from rotating library"
            )

        if do_rotate:
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
