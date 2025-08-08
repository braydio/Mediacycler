# Repository Audit and Documentation Scope Inventory

## Executive Summary
This audit inventories all components requiring documentation in the MediaCycler repository, identifies gaps between existing documentation and code, and catalogs external integrations and dependencies.

## Component Inventory

### 1. Encodarr
**Location**: `./Encodarr/`
**Purpose**: Flask-based transcoding notification service

**Key Files Present**:
- ✅ `app.py` - Main Flask application (8099 port)
- ✅ `transcode.sh` - Transcode script with Pi/Arch system detection
- ✅ `media_healthcheck.py` - Media file corruption detection
- ✅ `media_transcode.py` - Batch transcoding for Pi-incompatible codecs
- ✅ `Dockerfile` - Container build configuration
- ✅ `docker-compose.yml` - Service deployment configuration

### 2. MediaRotator  
**Location**: `./MediaRotator/`
**Purpose**: Disk-limited media rotation with cached imports

**Key Files Present**:
- ✅ `cache.py` - SQLite database operations
- ✅ `mdblist_fetcher.py` - MDBList API integration
- ✅ `radarr_handler.py` - Radarr API integration
- ✅ `sonarr_handler.py` - Sonarr API integration
- ✅ `README.md` - Component documentation (needs update)

**Missing Files** (referenced in README but not present):
- ❌ `media_rotator.py` - Main CLI entry point
- ❌ `utils.py` - Disk size, logging utilities

### 3. Scripts
**Location**: `./scripts/`
**Purpose**: Utility scripts for media management

**Key Files Present**:
- ✅ `tag_tv_genres.sh` - Jellyfin genre tagging automation

### 4. Threadfin
**Location**: `./threadfin/`
**Purpose**: Docker-deployed IPTV proxy service

**Key Files Present**:
- ✅ `docker-compose.yml` - Service deployment configuration

### 5. Trailarr
**Location**: `./trailarr/`
**Purpose**: Docker-deployed trailer management service

**Key Files Present**:
- ✅ `docker-compose.yml` - Service deployment configuration

### 6. Tunarr
**Location**: `./tunarr/` (Git Submodule)
**Purpose**: Third-party live TV channel creation tool

**Key Files Present**:
- ✅ `README.md` - Comprehensive upstream documentation
- ✅ `docker/dev.compose.yaml` - Development environment
- ✅ `docker/example.compose.yaml` - Production deployment example
- ✅ Extensive documentation in `docs/` directory

### 7. Project Root
**Key Files Present**:
- ✅ `example.env` - Environment variable template

**Missing Files**:
- ❌ Project-wide `README.md`
- ❌ ChatGPT context primer document

## Hard-Coded Configuration Audit

### Media Paths
- **Media Root**: `/mnt/netstorage/Media` (consistent across all components)
- **Rotating Movies**: `/mnt/netstorage/Media/RotatingMovies` (Radarr)
- **Rotating TV**: `/mnt/netstorage/Media/RotatingTV` (Sonarr) 
- **Transcoded Output**: `/mnt/netstorage/Media/Transcoded` (Encodarr)
- **TV Media**: `/mnt/netstorage/Media/TV` (Scripts, Trailarr)
- **Movies Media**: `/mnt/netstorage/Media/Movies` (Trailarr)

### Service Ports
- **Encodarr**: 8099 (Flask server)
- **Threadfin**: 34400
- **Trailarr**: 7889
- **Tunarr Dev**: 8000 (backend), 5173 (frontend)
- **Radarr**: 7878 (default)
- **Sonarr**: 8989 (default)
- **Jellyfin**: 8097 (tag_tv_genres.sh)

### External Integrations
- **Radarr/Sonarr APIs**: Movie/TV show management
- **MDBList API**: HD movie list source (`hd-movie-lists` user)
- **Jellyfin API**: Media server integration and tagging
- **Docker Hub**: Container image sources for all services

## Critical Discrepancies and Issues

### 1. MediaRotator Structure Mismatch
- **Issue**: README.md references `media_rotator.py` and `utils.py` as main entry points
- **Reality**: These files don't exist; only modular components present
- **Action**: Document current modular approach or create missing entry points

### 2. Encodarr Path Configuration
- **Issue**: `ALERTS_LOG = "/home/braydenchaffee/Projects/encodarr/alerts_log.log"` (outside repo)
- **Impact**: Container deployment will fail without volume mount
- **Action**: Document volume mount requirement or make configurable

### 3. Container Path Assumptions
- **Issue**: Encodarr calls `/app/transcode.sh` assuming containerized environment
- **Impact**: May fail in non-container deployments
- **Action**: Document deployment context requirements clearly

### 4. Trailarr Configuration Errors
- **Issue**: `restart: unles-stopped` (typo for "unless-stopped")
- **Issue**: Volume mappings incomplete (missing container targets)
- **Action**: Document corrected configuration

### 5. SQLite Cache Location
- **Issue**: MediaRotator stores cache at `~/.media_rotation_cache.db`
- **Impact**: Not persistent in containerized deployments
- **Action**: Document volume mount requirements

## Dependency Matrix

### System Dependencies
- **Python 3.x**: Encodarr, MediaRotator, Scripts (ffprobe calls)
- **ffmpeg/ffprobe**: Encodarr, Scripts (media analysis/transcoding)
- **curl/jq**: Scripts (API interactions)
- **Docker & Docker Compose**: All containerized services
- **Node.js 22**: Tunarr development
- **pnpm/Bun**: Tunarr package management and runtime

### Python Dependencies
- **Flask**: Encodarr web server
- **requests**: MediaRotator API clients
- **sqlite3**: MediaRotator caching (built-in)

## Documentation Strategy Recommendations

### Priority 1: Critical Fixes
1. Create missing `media_rotator.py` CLI entry point
2. Document Encodarr volume mount requirements
3. Fix Trailarr docker-compose.yml syntax and volumes
4. Create project-wide README.md

### Priority 2: Comprehensive Documentation
1. Document all hard-coded paths and override methods
2. Create ChatGPT context primer with architecture overview
3. Extend MediaRotator README with actual file structure
4. Document development vs. production deployment differences

### Priority 3: Integration Documentation  
1. Document API key requirements and setup procedures
2. Create troubleshooting guides for each component
3. Document media folder structure expectations
4. Create backup/recovery procedures for SQLite cache

## File Count Summary
- **Total Components**: 6 (5 custom + 1 third-party)
- **Total Files Audited**: 23 key configuration and code files
- **Missing Critical Files**: 3 (media_rotator.py, utils.py, project README)
- **Configuration Issues Found**: 5 major discrepancies
- **External Integrations**: 4 (Radarr, Sonarr, Jellyfin, MDBList)

This inventory provides the foundation for comprehensive documentation development with clear priorities and specific remediation actions.
