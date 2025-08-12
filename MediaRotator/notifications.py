"""Utilities for user notifications and change tracking."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# Determine whether desktop notifications should be sent
NOTIFICATIONS_ENABLED = os.getenv("ENABLE_NOTIFICATIONS", "true").lower() not in {
    "0",
    "false",
    "no",
}

# File updated with the timestamp of the last media change
DEFAULT_TIMESTAMP = Path(__file__).resolve().parent.parent / "last_media_change.txt"
TIMESTAMP_FILE = Path(os.getenv("MEDIA_CHANGE_FILE", DEFAULT_TIMESTAMP))


def notify_change(message: str) -> None:
    """Send a desktop notification and update the change timestamp.

    Parameters
    ----------
    message:
        The message to display if notifications are enabled.
    """
    timestamp = datetime.now().isoformat()

    if NOTIFICATIONS_ENABLED and shutil.which("notify-send"):
        try:
            subprocess.run(["notify-send", message], check=False)
        except Exception as exc:  # pragma: no cover - notification failures are non-critical
            print(f"⚠️ Failed to send notification: {exc}")

    try:
        TIMESTAMP_FILE.write_text(timestamp)
    except Exception as exc:  # pragma: no cover - file write errors are non-critical
        print(f"⚠️ Failed to update change timestamp: {exc}")

