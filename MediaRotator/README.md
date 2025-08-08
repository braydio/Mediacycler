# MediaRotator

## Overview

MediaRotator is an intelligent disk space management system that maintains 4TB quotas for rotating media collections while preventing duplicate imports through SQLite caching.

- **Purpose**: Automated media rotation with disk quota enforcement
- **Integration**: Connects MDBList curated content with Radarr/Sonarr APIs
- **Status**: Production-ready modular Python components

## Features

Intelligent content lifecycle management:

- **Quota Management**: Enforces 4TB limits on rotating media folders
- **Import Caching**: SQLite database prevents duplicate content acquisition
- **API Integration**: Seamless Radarr/Sonarr media addition and search triggering
- **Content Discovery**: MDBList `hd-movie-lists` integration for quality content
- **Modular Design**: Separate components for cache, API handlers, and content fetching
- **Automated Cleanup**: Removes oldest entries when quota exceeded

## Architecture / How it works

Modular Python architecture with SQLite persistence:

### Core Components

- **cache.py**: SQLite database operations for import tracking
- **radarr_handler.py**: Radarr API integration for movie management
- **sonarr_handler.py**: Sonarr API integration for TV show management
- **mdblist_fetcher.py**: MDBList API client for content discovery

### Data Flow

1. **Disk monitoring**: Check storage usage for rotating media folders
2. **Quota enforcement**: Remove oldest cached entries when over 4TB limit
3. **Content discovery**: Fetch curated lists from MDBList API
4. **Cache validation**: Check SQLite database to prevent duplicate imports
5. **Media addition**: Add new content via Radarr/Sonarr APIs
6. **Search triggering**: Initiate download process for added content
7. **Cache update**: Record successful additions with metadata

### External Dependencies

- **Radarr API**: Movie collection management and search triggering
- **Sonarr API**: TV show collection management and search triggering
- **MDBList API**: Curated HD movie and TV show list source
- **SQLite**: Local caching and import history persistence

## Prerequisites

System requirements for media rotation management:

### System Requirements

- **Operating System**: Linux with Python 3.6+
- **Memory**: 512MB RAM minimum for SQLite operations
- **Storage**: Access to media paths (`/mnt/netstorage/Media/Rotating*`)
- **Network**: API access to Radarr, Sonarr, and MDBList services

### Dependencies

```bash
# Python packages
pip install requests sqlite3

# System packages (for development)
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
```

### API Keys & Credentials

Required for full functionality:

- **RADARR_API_KEY**: Radarr instance API access
- **SONARR_API_KEY**: Sonarr instance API access
- **MDBLIST_API_KEY**: MDBList API for content discovery

## Installation

### Python Module Installation

```bash
# Navigate to MediaRotator directory
cd MediaRotator

# Create Python environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install requests

# Initialize SQLite cache
python3 -c "from cache import initialize_cache_db; initialize_cache_db()"
```

### Manual Installation

```bash
# Install system dependencies
sudo apt install -y python3-requests python3-sqlite3

# Set up cache directory
mkdir -p ~/.cache/media_rotator
chmod 700 ~/.cache/media_rotator
```

## Configuration

### Directory/Quota Setup

| Type     | Tool   | Path                                   | Max Size |
| -------- | ------ | -------------------------------------- | -------- |
| Movies   | Radarr | `/mnt/netstorage/Media/RotatingMovies` | 4 TB     |
| TV Shows | Sonarr | `/mnt/netstorage/Media/RotatingTV`     | 4 TB     |

### Environment Variables

```bash
# Radarr Configuration
export RADARR_API_KEY="YOUR_RADARR_API_KEY"
export RADARR_URL="http://localhost:7878"
export RADARR_QUALITY_PROFILE_ID="1"

# Sonarr Configuration
export SONARR_API_KEY="YOUR_SONARR_API_KEY"
export SONARR_URL="http://localhost:8989"
export SONARR_QUALITY_PROFILE_ID="1"
export SONARR_LANGUAGE_PROFILE_ID="1"

# MDBList Configuration
export MDBLIST_API_KEY="YOUR_MDBLIST_API_KEY"
export MDBLIST_USER="hd-movie-lists"

# Storage Paths
export ROTATING_MOVIES_PATH="/mnt/netstorage/Media/RotatingMovies"
export ROTATING_TV_PATH="/mnt/netstorage/Media/RotatingTV"
export CACHE_DB_PATH="$HOME/.media_rotation_cache.db"
```

### SQLite Cache Schema

```sql
CREATE TABLE imported_media (
    id TEXT PRIMARY KEY,           -- IMDb/TVDB ID
    type TEXT NOT NULL CHECK(type IN ('movie', 'show')),
    title TEXT,
    list_name TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage

### Basic Operations

```bash
# Initialize cache database
cd MediaRotator
python3 -c "from cache import initialize_cache_db; initialize_cache_db()"

# Check cache contents
python3 -c "import sqlite3; conn = sqlite3.connect('~/.media_rotation_cache.db'); print(conn.execute('SELECT COUNT(*) FROM imported_media').fetchone())"

# Test API connections
python3 -c "from radarr_handler import test_connection; test_connection()"
python3 -c "from sonarr_handler import test_connection; test_connection()"
```

### API Examples

```python
# Add movie to cache and Radarr
from cache import add_to_cache
from radarr_handler import add_movie, search_movie

# Cache the import
add_to_cache('tt1234567', 'movie', 'Example Movie', 'HD Action Movies')

# Add to Radarr and trigger search
if add_movie('tt1234567'):
    search_movie('tt1234567')
    print("Movie added and search triggered")
```

```python
# Check disk usage and cleanup
import os
from cache import get_oldest_entry, remove_from_cache

def check_disk_usage(path):
    """Check disk usage for given path"""
    statvfs = os.statvfs(path)
    free_bytes = statvfs.f_frsize * statvfs.f_bavail
    total_bytes = statvfs.f_frsize * statvfs.f_blocks
    used_bytes = total_bytes - free_bytes
    return used_bytes / (1024**4)  # TB

# Monitor and cleanup
if check_disk_usage('/mnt/netstorage/Media/RotatingMovies') > 4.0:
    oldest = get_oldest_entry('movie')
    if oldest:
        remove_from_cache(oldest[0])
        print(f"Removed oldest entry: {oldest[1]}")
```

### Integration Examples

```bash
# Shell script for automated rotation
#!/bin/bash
cd /path/to/MediaRotator
source venv/bin/activate

# Run movie rotation
python3 -c "
from cache import *
from radarr_handler import *
from mdblist_fetcher import *

# Check quota and rotate if needed
# Add implementation here
"
```

## Automation / Operations

### Script Workflow (per type: movie/show)

1. **Check disk size of media folder**
2. **If over 4TB**: Delete oldest imported entry (and remove from Radarr/Sonarr too)
3. **Fetch lists**: Get curated content from `HD Movie Lists` on MDBList
4. **Load cache**: Read previously imported IDs from SQLite
5. **Process lists**: For each list, find content not in Radarr/Sonarr AND not in cache
6. **Add content**: Add via API, trigger search, and record in cache
7. **Exit**: Process one item per run (prevents flooding)

### Cron Job Setup

```bash
# Add to crontab for automated rotation
# Run every 6 hours
0 */6 * * * cd /path/to/MediaRotator && python3 -c "from cache import *; from radarr_handler import *; from mdblist_fetcher import *;" > /tmp/media_rotator.log 2>&1
```

### Monitoring

```bash
# Check disk usage
df -h /mnt/netstorage/Media/Rotating*

# View cache database size
du -h ~/.media_rotation_cache.db

# Count cached entries
sqlite3 ~/.media_rotation_cache.db "SELECT COUNT(*) FROM imported_media;"

# View most recent imports
sqlite3 ~/.media_rotation_cache.db "SELECT title, imported_at FROM imported_media ORDER BY imported_at DESC LIMIT 10;"
```

## Troubleshooting

### Common Issues

#### API Connection Failures

**Symptoms**: HTTP errors, connection timeouts
**Solutions**:

```bash
# Verify API keys
echo $RADARR_API_KEY
echo $SONARR_API_KEY

# Check service connectivity
curl -s http://localhost:7878/api/v3/system/status?apikey=$RADARR_API_KEY | jq
curl -s http://localhost:8989/api/v3/system/status?apikey=$SONARR_API_KEY | jq
```

#### SQLite Database Errors

**Symptoms**: Integrity errors, disk permission issues
**Solutions**:

```bash
# Check database permissions
ls -la ~/.media_rotation_cache.db

# Verify database integrity
sqlite3 ~/.media_rotation_cache.db "PRAGMA integrity_check;"

# Create new database if corrupted
rm ~/.media_rotation_cache.db
python3 -c "from cache import initialize_cache_db; initialize_cache_db()"
```

#### Disk Space Calculation Issues

**Symptoms**: Quota not enforced correctly, disk space calculation errors
**Solutions**:

```bash
# Manually check disk usage
du -sh /mnt/netstorage/Media/RotatingMovies
du -sh /mnt/netstorage/Media/RotatingTV

# Verify path exists and is mounted
mount | grep netstorage
ls -la /mnt/netstorage/Media/
```

### Log Analysis

```bash
# Set up logging for troubleshooting
python3 -c "
import logging
logging.basicConfig(
    filename='/tmp/mediarotator_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
from cache import initialize_cache_db
initialize_cache_db()
"

# View debug logs
tail -f /tmp/mediarotator_debug.log
```

## Security

### Authentication

- **API Keys**: Store Radarr/Sonarr API keys securely in environment variables
- **File System**: Cache database has restricted permissions (600)
- **Network**: API calls only to trusted local services

### Data Protection

- **No Sensitive Data**: Cache only stores media IDs and titles
- **Local Storage**: SQLite database remains on local system
- **Error Handling**: Prevents SQL injection through parameterized queries

### Security Best Practices

- Keep Python and dependencies updated
- Use virtual environments for isolation
- Never expose API keys in scripts or logs
- Restrict cache database file permissions

## Roadmap

Planned features and improvements:

- [ ] **Q1 2024**: Multiple watchlist support for different genres
- [ ] **Q2 2024**: Configurable quota sizes per media type
- [ ] **Q3 2024**: Ratings-based prioritization for retention
- [ ] **Q4 2024**: Web UI for monitoring and manual management

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/mediarotator-enhancement`
3. Follow modular architecture patterns
4. Add tests for new functionality
5. Submit a pull request with detailed description

### Development Setup

```bash
# Development environment
python3 -m venv venv
source venv/bin/activate
pip install requests pytest

# Run tests
pytest tests/
```

## License

This project is licensed under the MIT License - see [LICENSE](../LICENSE) file for details.

---

## Acceptance Criteria

- [ ] API integration works with Radarr and Sonarr
- [ ] SQLite cache prevents duplicate imports
- [ ] Disk quota monitoring accurately enforces 4TB limits
- [ ] Content rotation removes oldest entries when quota exceeded
- [ ] MDBList integration provides quality content recommendations
- [ ] Cache persists between runs and system restarts
- [ ] Environment variables provide clean configuration
- [ ] Error handling captures and logs issues appropriately
- [ ] Documentation includes all key usage patterns
- [ ] Integration examples work as described
