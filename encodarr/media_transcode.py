import os
import subprocess
import json
import shutil
from datetime import datetime

MEDIA_DIR = "/mnt/netstorage/Media"
SUBDIRS = ["TV", "Movies", "Music"]
SUPPORTED_CODECS = {"h264", "mpeg4", "mpeg2video", "vp8"}  # add "hevc" for Pi 5+
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm"}
LOGFILE = os.path.join(MEDIA_DIR, "transcoded_files.log")


def get_codec_info(filepath):
    """Returns (vcodec, acodec) for the file, or (None, None) if error."""
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "json",
            filepath,
        ]
        vdata = subprocess.check_output(cmd).decode()
        vcodec = json.loads(vdata)["streams"][0]["codec_name"]

        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name",
            "-of",
            "json",
            filepath,
        ]
        adata = subprocess.check_output(cmd).decode()
        acodec = json.loads(adata)["streams"][0]["codec_name"]
        return vcodec, acodec
    except Exception as e:
        print(f"Error getting codec info for {filepath}: {e}")
        return None, None


def transcode_file(filepath):
    out_temp = filepath + ".pi_tmp.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        filepath,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "22",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        out_temp,
    ]
    print(f"Transcoding {filepath} to {out_temp} ...")
    try:
        subprocess.run(cmd, check=True)
        print(f"  Transcoded: {out_temp}")
        return out_temp
    except subprocess.CalledProcessError as e:
        print(f"  Failed to transcode {filepath}: {e}")
        if os.path.exists(out_temp):
            os.remove(out_temp)
        return None


def replace_and_log(orig, transcoded, vcodec, logf):
    # Make a backup before replacing
    backup = orig + ".bak"
    shutil.move(orig, backup)
    shutil.move(transcoded, orig)
    logline = (
        f"{datetime.now().isoformat()} | {orig} | {vcodec} -> h264 (backup: {backup})"
    )
    print(f"  Replaced original with transcoded file. Backup at {backup}")
    logf.write(logline + "\n")


def main():
    with open(LOGFILE, "a") as logf:
        for sub in SUBDIRS:
            folder = os.path.join(MEDIA_DIR, sub)
            for root, dirs, files in os.walk(folder):
                for name in files:
                    ext = os.path.splitext(name)[1].lower()
                    if ext in VIDEO_EXTS:
                        filepath = os.path.join(root, name)
                        vcodec, acodec = get_codec_info(filepath)
                        if vcodec and vcodec not in SUPPORTED_CODECS:
                            print(
                                f"File {filepath} uses {vcodec}, not Pi-supported. Will transcode."
                            )
                            out = transcode_file(filepath)
                            if out:
                                replace_and_log(filepath, out, vcodec, logf)
                            else:
                                print(
                                    f"  Skipped replace due to transcode failure: {filepath}"
                                )
                        else:
                            print(f"File {filepath} is compatible: {vcodec}")
    print(f"Done. Log written to {LOGFILE}")


if __name__ == "__main__":
    main()
