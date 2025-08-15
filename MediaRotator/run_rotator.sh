#!/usr/bin/env bash
# Simple scheduler for MediaRotator; runs the rotation script every hour.
set -e

while true; do
  python media_rotator.py
  sleep 3600
done
