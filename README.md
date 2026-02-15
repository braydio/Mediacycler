# Mediacycler

Multi-service media suite orchestrated with Docker Compose.

## Structure

- `encodarr/`
- `mediarotator/`
- `threadfin/`
- `trailarr/`
- `docker-compose.yml`
- `example.env`

## Quick start

Build images:

```bash
docker-compose build
```

Run services:

```bash
docker-compose up -d
```

Stop services:

```bash
docker-compose down
```

Open a shell in a service (replace `encodarr` with the target service name):

```bash
docker-compose run --rm encodarr /bin/bash
```

## Notes

- Set Radarr/Sonarr environment variables in `example.env` (copy to `.env`).
- Tunarr runs strictly as a container; configuration and data should be mounted from the host if enabled in `docker-compose.yml`.

## Shelf TUI

Review the rotating media "Shelf" and mark items for deletion.

```bash
pip install -r mediarotator/requirements.txt
python -m tui.shelf_tui
```

## Shelf Web UI (Skeleton)

```bash
pip install -r mediarotator/requirements.txt
python -m api.web
```

Open `http://localhost:8099/shelf`.

Docker Compose (web UI on port 8100):

```bash
docker-compose up -d shelf
```

Open `http://localhost:8100/shelf`.

## License

See `LICENSE` for details.
