# Custom Config

---

## Set custom configuration in .rotator_config.json

Optional support to use mdblist (not yet tested/implemented)

- Default uses Trakt.tv trending list

```
  "use_mdblist": false,
  "movie_lists": ["trending"],
  "show_lists": ["trending"],
```

Define paths for TV Shows and Movies libraries

```
  "movie_root": "/mnt/netstorage/Media/RotatingMovies",
  "show_root": "/mnt/netstorage/Media/RotatingShows",
```

Define remaining disk space to trigger deletions

```
  "movie_disk_limit_gb": 100,
  "show_disk_limit_gb": 50
```

## Seedbox sync (optional)

MediaRotator can sync validated media from a seedbox staging area to local rotating paths.
The settings below may be set in `.rotator_config.json` or via environment variables.

```
  "seedbox": {
    "enabled": true,
    "host": "seedbox.example.com",
    "user": "seeduser",
    "port": 22,
    "movies_path": "~/media/movies",
    "tv_path": "~/media/tv",
    "movies_dest": "/mnt/netstorage/Media/RotatingMovies",
    "tv_dest": "/mnt/netstorage/Media/RotatingTV",
    "cleanup_delay_hours": 12,
    "ssh_key_path": "/root/.ssh/id_rsa",
    "ssh_strict_host_key_checking": "accept-new",
    "ssh_extra_args": ""
  }
```

## Optional preference files

`UserPrefs_Lists.yaml` can define list names for movies and TV (primary/spice). When present, the rotator will
prefer those lists for MDBList (by list title) or Trakt (by list name) if a Trakt user is configured.

`.userPrefs.yaml` can provide a Trakt user, list names, and optional storage/cadence defaults. The file may be
stored as a fenced YAML block (```yaml ... ```).

{

"movie_root": "/mnt/netstorage/Media/RotatingMovies",
"show_root": "/mnt/netstorage/Media/RotatingShows",
}
