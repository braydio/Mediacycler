#!/bin/bash
set -euo pipefail

# Recursively scan for .ass subtitle files and convert to .srt
# Requires: ffmpeg

MEDIA_DIR="/mnt/netstorage/Media"

find "$MEDIA_DIR" -type f -name "*.ass" | while IFS= read -r assfile; do
    srtfile="${assfile%.*}.srt"

    if [ -f "$srtfile" ]; then
        echo "Skipping (already exists): $srtfile"
        continue
    fi

    echo "Converting: $assfile -> $srtfile"
    if ffmpeg -y -i "$assfile" "$srtfile" >/dev/null 2>&1; then
        echo "Success: $srtfile"
    else
        echo "Failed: $assfile"
    fi
done
