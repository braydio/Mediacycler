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

## Optional preference files

`UserPrefs_Lists.yaml` can define list names for movies and TV (primary/spice). When present, the rotator will
prefer those lists for MDBList (by list title) or Trakt (by list name) if a Trakt user is configured.

`.userPrefs.yaml` can provide a Trakt user, list names, and optional storage/cadence defaults. The file may be
stored as a fenced YAML block (```yaml ... ```).

{

"movie_root": "/mnt/netstorage/Media/RotatingMovies",
"show_root": "/mnt/netstorage/Media/RotatingShows",
}
