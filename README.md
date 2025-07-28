---

## Disk-Limited Media Rotation with Cached Imports

### ✅ Directory/Quota Setup

| Type     | Tool   | Path                                   | Max Size |
| -------- | ------ | -------------------------------------- | -------- |
| Movies   | Radarr | `/mnt/netstorage/Media/RotatingMovies` | 4 TB     |
| TV Shows | Sonarr | `/mnt/netstorage/Media/RotatingTV`     | 4 TB     |

---

### 🗂️ Caching Strategy

- **SQLite** for simplicity, portability, and future extensibility.
- Schema:

```sql
CREATE TABLE imported_media (
    id TEXT PRIMARY KEY,     -- IMDb ID or TVDB ID
    type TEXT,               -- 'movie' or 'show'
    title TEXT,
    list_name TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

- Tracks what has been imported, even if Radarr/Sonarr removes it later.

---

### 🧠 Script Workflow (per type: movie/show)

1. **Check disk size of media folder**
2. If over 4TB delete oldest imported entry (and remove from Radarr/Sonarr too)
3. Fetch lists from `HD Movie Lists` on mdblist
4. Load cache of imported IDs from SQLite
5. For each list:

   - If movie/show not in Radarr/Sonarr **and** not in cache:

     - Add it via API
     - Trigger search
     - Add to cache
     - Break (do one per run)

6. Exit

---

### Structure

**Modules:**

- `media_rotator.py` — CLI entry
- `cache.py` — SQLite manager
- `radarr_handler.py` / `sonarr_handler.py` — API interaction
- `mdblist_fetcher.py` — Get lists + entries from mdblist
- `utils.py` — Disk size, logging, etc
