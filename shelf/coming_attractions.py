from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass

from dotenv import load_dotenv

from shelf.scanner import resolve_paths


@dataclass
class ComingAttraction:
    title: str
    path: str
    kind: str
    state: str


def _build_ssh_command() -> list[str]:
    load_dotenv()
    host = os.getenv("SEEDBOX_HOST")
    user = os.getenv("SEEDBOX_USER")
    port = os.getenv("SEEDBOX_PORT", "22")
    key_path = os.getenv("SEEDBOX_SSH_KEY_PATH")
    strict = os.getenv("SEEDBOX_SSH_STRICT_HOST_KEY_CHECKING", "accept-new")
    extra_args = os.getenv("SEEDBOX_SSH_EXTRA_ARGS", "")

    if not host or not user:
        return []

    cmd = ["ssh", "-p", str(port)]
    if key_path:
        cmd += ["-i", key_path]
    if strict:
        cmd += ["-o", f"StrictHostKeyChecking={strict}"]
    if extra_args:
        cmd += shlex.split(extra_args)
    cmd.append(f"{user}@{host}")
    return cmd


def _list_remote(remote_path: str, latest_first: bool = True) -> list[str]:
    ssh_cmd = _build_ssh_command()
    if not ssh_cmd:
        return []
    ls_flag = "-1t" if latest_first else "-1"
    remote_cmd = f"ls {ls_flag} {shlex.quote(remote_path)}"
    try:
        result = subprocess.run(
            ssh_cmd + ["bash", "-lc", remote_cmd],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=12,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _get_paths() -> dict[str, tuple[str, str]]:
    load_dotenv()
    return {
        "movie-downloading": ("movie", os.getenv("SEEDBOX_INCOMPLETE_MOVIES_PATH", "")),
        "tv-downloading": ("tv", os.getenv("SEEDBOX_INCOMPLETE_TV_PATH", "")),
        "movie-downloaded": ("movie", os.getenv("SEEDBOX_MOVIES_PATH", "")),
        "tv-downloaded": ("tv", os.getenv("SEEDBOX_TV_PATH", "")),
    }


def _is_synced_locally(title: str, kind: str) -> bool:
    movies_root, tv_root = resolve_paths()
    root = movies_root if kind == "movie" else tv_root
    if not root:
        return False
    return os.path.exists(os.path.join(root, title))


def list_coming_attractions(limit: int = 10) -> list[ComingAttraction]:
    sources = _get_paths()
    items: list[ComingAttraction] = []

    for source_name, (kind, path) in sources.items():
        if not path:
            continue
        state = "downloading" if source_name.endswith("downloading") else "downloaded"
        for name in _list_remote(path, latest_first=True):
            if len(items) >= limit:
                return items[:limit]
            if state == "downloaded" and _is_synced_locally(name, kind):
                continue
            items.append(
                ComingAttraction(
                    title=name,
                    path=f"{path.rstrip('/')}/{name}",
                    kind=kind,
                    state=state,
                )
            )
    return items[:limit]


def coming_attractions_note(items: list[ComingAttraction]) -> str | None:
    if items:
        return None
    load_dotenv()
    host = os.getenv("SEEDBOX_HOST")
    user = os.getenv("SEEDBOX_USER")
    if not host or not user:
        return "Coming Attractions unavailable: set SEEDBOX_HOST and SEEDBOX_USER."
    paths = _get_paths()
    if not any(path for _kind, path in paths.values()):
        return "Coming Attractions unavailable: configure SEEDBOX_*_PATH variables."
    return "No downloading or downloaded-unsynced items found."
