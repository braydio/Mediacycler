# Expected Issues Log

- 2026-01-18 Encodarr container mismatch (port 8099, log path, media mount, x86 detection). Status: fixed in `docker-compose.yml`, `encodarr/app.py`, `encodarr/transcode.sh`.
- 2026-01-18 MediaRotator rotation dry-run + show loop indentation + path casing in cron/docs. Status: fixed in `mediarotator/media_rotator.py`, `scripts/setup-cron.sh`, `README.md`.
- 2026-01-18 MediaRotator .env loading required python-dotenv; added fallback loader to avoid missing-env failures. Status: fixed in `mediarotator/media_rotator.py`.
- 2026-01-18 MediaRotator container default URLs used localhost; added Docker-aware defaults and host gateway mapping. Status: fixed in `mediarotator/radarr_handler.py`, `mediarotator/sonarr_handler.py`, `docker-compose.yml`.
- 2026-01-18 Root folder path mismatches were easy to misconfigure; added explicit env options in examples and compose. Status: fixed in `example.env`, `mediarotator/.env.example`, `docker-compose.yml`.
- 2026-01-18 Trakt fallback failed silently without `TRAKT_CLIENT_ID`; now warns and skips requests. Status: fixed in `mediarotator/trakt_fetcher.py`.
- 2026-01-18 Directory size checks could be slow; added optional `du`-based sizing via `ROTATOR_DIR_SIZE_METHOD=du`. Status: fixed in `mediarotator/media_rotator.py`.
- 2026-01-18 Unpinned service images; added tag environment overrides for threadfin/trailarr. Status: fixed in `docker-compose.yml`, `example.env`, `README.md`.
