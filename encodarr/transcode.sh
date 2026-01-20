#!/bin/bash

INPUT="$1"
BASENAME=$(basename "$INPUT")
EXT="${BASENAME##*.}"
FILENAME="${BASENAME%.*}"
OUTPUT_DIR="/mnt/netstorage/Media/Transcoded"
mkdir -p "$OUTPUT_DIR"

OUTPUT="$OUTPUT_DIR/${FILENAME}.mp4"
HOSTNAME=$(uname -n)
IS_PI=false
IS_X86=false

# Detect system type
if [[ "$(uname -m)" == "armv7l" || "$(uname -m)" == "aarch64" ]]; then
  IS_PI=true
else
  IS_X86=true
fi

# Detect codecs
VIDEO_CODEC=$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name -of default=nk=1:nw=1 "$INPUT")
AUDIO_CODEC=$(ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=nk=1:nw=1 "$INPUT")

NEEDS_VIDEO_TRANSCODE=false
NEEDS_AUDIO_TRANSCODE=false

if [[ "$VIDEO_CODEC" == "hevc" || "$VIDEO_CODEC" == "vp9" ]]; then
  NEEDS_VIDEO_TRANSCODE=true
fi

if [[ "$AUDIO_CODEC" == "eac3" || "$AUDIO_CODEC" == "dts" ]]; then
  NEEDS_AUDIO_TRANSCODE=true
fi

# --- On Pi: Do only lightweight jobs ---
if $IS_PI; then
  if ! $NEEDS_VIDEO_TRANSCODE && $NEEDS_AUDIO_TRANSCODE; then
    echo "[Pi] Transcoding AUDIO ONLY for $INPUT"
    ffmpeg -hide_banner -loglevel error \
      -i "$INPUT" \
      -c:v copy \
      -c:a aac -b:a 128k \
      -movflags +faststart \
      "$OUTPUT"
    echo "[Pi] Done: $OUTPUT"
    exit 0
  else
    echo "[Pi] Too heavy to transcode. Moving to ToTranscode directory..."
    cp "$INPUT" /mnt/netstorage/Media/ToTranscode/
    echo "[Pi] Moved to /mnt/netstorage/Media/ToTranscode/"
    exit 0
  fi
fi

# --- On x86: Transcode everything ---
if $IS_X86; then
  echo "[x86] Transcoding $INPUT"
  ffmpeg -hide_banner -loglevel warning \
    -i "$INPUT" \
    -c:v libx264 -preset slow -crf 23 \
    -c:a aac -b:a 192k \
    -movflags +faststart \
    "$OUTPUT"
  echo "[Arch] Done: $OUTPUT"
  exit 0
fi

echo "[Unknown System] Skipping."
exit 1
