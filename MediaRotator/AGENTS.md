# Repository Guidelines

This document is a concise contributor guide for the Mediacycler multi-service repository.

## Project Structure & Module Organization
- Root: contains `docker-compose.yml` and service folders: `Encodarr/`, `MediaRotator/`, `trailarr/`, `threadfin/`.
- Service layout: source code, `Dockerfile`, and `tests/` live inside each service directory (e.g., `MediaRotator/`).
- Shared assets: `docs/` and `logs/` at repository root.

## Build, Test, and Development Commands
- Build all images: `docker-compose build` — builds service images.
- Run services: `docker-compose up -d` — starts services in background.
- Stop services: `docker-compose down` — stops and removes containers.
- Shell into a service: `docker-compose run --rm encodarr /bin/bash` (replace `encodarr`).
- Run tests per service: `docker-compose run --rm <service> pytest -q` (Python) or `docker-compose run --rm <service> npm test`.
 - Run tests per service: `docker-compose run --rm <service> pytest -q` (Python) or `docker-compose run --rm <service> npm test`.
 - Run directly: `python media_rotator.py` from the `MediaRotator/` folder to run the rotator without Docker.

## Coding Style & Naming Conventions
- Python services: 4-space indentation, modules in `lowercase_with_underscores`.
- Bash scripts: POSIX style, include `set -euo pipefail` at top.
- Dockerfiles: use consistent base images and include clear `LABEL` and version notes.
- Formatting: prefer `black`/`flake8` for Python when present; run linters inside service containers.

## Testing Guidelines
- Test frameworks: `pytest` for Python services; tests live under each service `tests/`.
- Naming: `test_<module>.py` and `Test<ClassName>` for classes.
- Aim for deterministic tests and pin deps in `requirements.txt` or `package.json`.

## Commit & Pull Request Guidelines
- Commit messages: imperative mood, e.g. `feat(encodarr): add transcoding option`.
- PRs: include description, linked issue(s), list of changes, and screenshots for UI work; run local tests before opening.

## Security & Configuration Tips
- Never commit secrets; use environment variables or a `.env` file excluded by `.gitignore`.
- Validate configs: `docker-compose config` before pushing.

Configuring Trakt lists
- You can control which Trakt lists the rotator uses via `.rotator_config.json` in the service folder.
- Default behavior: if no config is present the rotator uses Trakt `trending` lists for movies and shows.
- Example: copy `.rotator_config.json.example` to `MediaRotator/.rotator_config.json` and edit `movie_lists` and `show_lists`.
- To force using MDBList instead, set `"use_mdblist": true` in the config.

Disk usage limits
- Configure rotating library paths and limits in `.rotator_config.json`:
  - `movie_root`: path used when adding movies to Radarr (must match a Radarr root folder).
  - `movie_disk_limit_gb`: maximum GB allowed for rotating movies (rotator will delete oldest until under limit).
  - Same keys exist for shows: `show_root` and `show_disk_limit_gb`.
 - Copy `.rotator_config.json.example` and edit; mount these files into containers so the rotator and Radarr see the same paths.

Use a `.env` file for local config
- Place a `.env` in the service folder (example `MediaRotator/.env`) with keys like `RADARR_API_KEY=...` and `SONARR_API_KEY=...`.
- The project uses `python-dotenv` (listed in `requirements.txt`); install with `pip install -r requirements.txt` to load `.env` automatically.

## Quick Start
- Fork/branch, implement changes, run `docker-compose build` and `docker-compose up -d`, run service tests, then open a PR.
