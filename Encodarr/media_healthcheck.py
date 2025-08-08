import os
import subprocess

# Paths to scan
MEDIA_DIR = "/mnt/netstorage/Media"
SUBDIRS = ["TV", "Movies", "Music"]

# File extensions to check with ffmpeg
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}
AUDIO_EXTS = {".mp3", ".flac", ".aac", ".ogg", ".m4a", ".wav", ".wma"}

LOGFILE = os.path.join(MEDIA_DIR, "bad_files.log")


def ffmpeg_check(filepath):
    """Use ffmpeg to check if a media file can be decoded."""
    try:
        # This will try to decode the whole file quickly, but not output data
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", filepath, "-f", "null", "-"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # ffmpeg sends errors to stderr
        if proc.returncode != 0 or proc.stderr:
            return proc.stderr.strip() or f"ffmpeg error code {proc.returncode}"
    except Exception as e:
        return str(e)
    return None


def check_file(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext in VIDEO_EXTS or ext in AUDIO_EXTS:
        return ffmpeg_check(filepath)
    else:
        try:
            with open(filepath, "rb") as f:
                f.read(1024)
            return None
        except Exception as e:
            return str(e)


def walk_and_check():
    bad_files = []
    for sub in SUBDIRS:
        folder = os.path.join(MEDIA_DIR, sub)
        for root, dirs, files in os.walk(folder):
            for name in files:
                filepath = os.path.join(root, name)
                result = check_file(filepath)
                if result:
                    print(f"CORRUPT: {filepath} — {result}")
                    bad_files.append(f"{filepath}: {result}")
    # Write all bad files to log
    with open(LOGFILE, "w") as log:
        for line in bad_files:
            log.write(line + "\n")
    print(f"Done. {len(bad_files)} corrupt or unreadable files found. See {LOGFILE}")


if __name__ == "__main__":
    walk_and_check()
