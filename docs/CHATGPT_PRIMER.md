# MediaCycler ChatGPT Primer

## System Overview
MediaCycler is a comprehensive media automation suite that manages, processes, and serves digital content across multiple services. The system integrates with Servarr applications (Radarr, Sonarr) and media servers (Jellyfin, Plex) to provide automated content lifecycle management.

## Architecture Components

### Core Services
- **Encodarr**: Flask-based transcoding notification service (Port 8099)
- **MediaRotator**: Intelligent disk space management with cached imports
- **Threadfin**: IPTV proxy service (Port 34400)
- **Trailarr**: Trailer management service (Port 7889)
- **Tunarr**: Live TV channel creation service (Third-party integration)

### Utility Scripts
- **tag_tv_genres.sh**: Automated Jellyfin genre tagging and collection management

## Media Storage Architecture

### Standard Media Paths
```
/mnt/netstorage/Media/
├── Movies/                  # Primary movie storage (Trailarr)
├── TV/                     # Primary TV storage (Scripts, Trailarr)
├── RotatingMovies/         # 4TB quota-managed movies (MediaRotator)
├── RotatingTV/             # 4TB quota-managed TV shows (MediaRotator)
└── Transcoded/             # Processed media output (Encodarr)
```

### Service Integration Map
```
External APIs ──→ MediaRotator ──→ Radarr/Sonarr ──→ Media Storage
                                       ↓
Jellyfin/Plex ←── tag_tv_genres.sh ←──┘
      ↓
Encodarr ←── Transcoding Notifications
      ↓
Threadfin/Tunarr ←── IPTV/Channel Services
```

## Key Integrations

### MDBList Integration
- **Purpose**: Source for curated HD movie lists
- **User**: `hd-movie-lists`
- **Usage**: MediaRotator fetches and processes movie recommendations
- **Rate Limits**: Managed through caching layer

### Radarr/Sonarr APIs
- **Movies**: http://localhost:7878 (Default)
- **TV Shows**: http://localhost:8989 (Default)
- **Functions**: Add media, trigger searches, quality profile management
- **Authentication**: API key-based

### Jellyfin Integration
- **Server**: http://192.168.1.198:8097
- **Functions**: Genre tagging, collection management, metadata updates
- **Libraries**: Automatic detection and processing

## Data Persistence

### SQLite Cache (MediaRotator)
```sql
CREATE TABLE imported_media (
    id TEXT PRIMARY KEY,           -- IMDb/TVDB ID
    type TEXT CHECK(type IN ('movie', 'show')),
    title TEXT,
    list_name TEXT,
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
- **Location**: `~/.media_rotation_cache.db`
- **Purpose**: Prevent duplicate imports across rotation cycles
- **Backup**: Manual process, consider volume mounts for containers

### Configuration Storage
- **Threadfin**: `./threadfin/data/conf/`
- **Trailarr**: `./trailarr/trailarr_data/`
- **Tunarr**: Internal database (varies by deployment)

## Service Ports and URLs

### Internal Services
- **Encodarr**: http://localhost:8099
- **Threadfin**: http://localhost:34400
- **Trailarr**: http://localhost:7889
- **Tunarr Dev**: Backend: http://localhost:8000, Frontend: http://localhost:5173

### External Dependencies
- **Radarr**: http://localhost:7878
- **Sonarr**: http://localhost:8989
- **Jellyfin**: http://192.168.1.198:8097

## Docker Deployment Patterns

### Standard Environment Variables
```bash
# Common across services
TZ=America/New_York
PUID=1000
PGID=1000

# Service-specific
RADARR_API_KEY=your_api_key_here
SONARR_API_KEY=your_api_key_here
```

### Volume Mount Patterns
```yaml
# Standard media access
- /mnt/netstorage:/mnt/netstorage

# Configuration persistence  
- ./service_data:/config

# Log access (Encodarr)
- /home/pi:/app/host_home_pi
```

## Workflow Patterns

### MediaRotator Cycle
1. **Check disk usage**: Monitor `/mnt/netstorage/Media/Rotating*` folders
2. **Cleanup if needed**: Remove oldest entries when over 4TB quota
3. **Fetch new content**: Query MDBList for HD movie/show recommendations
4. **Cache validation**: Check SQLite cache to prevent duplicates  
5. **API integration**: Add new content via Radarr/Sonarr APIs
6. **Search trigger**: Initiate content search and download
7. **Cache update**: Record successful additions

### Encodarr Processing
1. **Notification receipt**: Receive POST to `/notify` endpoint
2. **Parameter extraction**: Parse file path, video/audio codec info
3. **Script execution**: Run containerized transcode.sh with file path
4. **Output logging**: Record transcode results and errors
5. **File management**: Handle transcoded output placement

### Genre Tagging Automation
1. **Library scan**: Discover TV show folders by genre structure
2. **Jellyfin query**: Search for matching series in library
3. **Metadata update**: Apply genre tags based on folder structure
4. **Collection management**: Create/update genre-based collections
5. **Batch processing**: Handle multiple shows in single execution

## Common Issues and Solutions

### Path Resolution
- Container paths vs. host paths often cause confusion
- Always verify volume mounts match expected internal paths
- Use absolute paths in scripts and configuration

### API Rate Limiting
- MDBList API has usage restrictions
- Implement caching and request throttling
- Cache database prevents redundant API calls

### SQLite Database Location
- Default cache location not container-friendly
- Consider volume mounts or configurable paths
- Backup strategy needed for persistence

### Configuration Management
- Many services use hardcoded localhost URLs
- Environment variable substitution recommended
- Docker networking may require service name resolution

## Security Considerations

### API Key Management
- Store all credentials in environment variables
- Never commit real API keys to version control
- Use placeholders like `YOUR_API_KEY` in documentation

### Network Security
- Services typically bind to all interfaces (0.0.0.0)
- Consider firewall rules or reverse proxy
- Internal network segmentation recommended

### File System Security
- Media paths require read/write permissions
- Container user mapping critical for file access
- SQLite database needs write permissions

## Development Context

### Technology Stack
- **Backend**: Python (Flask), Shell scripting, SQLite
- **Frontend**: Various web UIs per service
- **Orchestration**: Docker Compose
- **APIs**: RESTful HTTP APIs for all integrations

### Code Organization
- Modular Python components in MediaRotator
- Shell scripts for system-level operations
- Docker Compose for service deployment
- Configuration through environment variables

### Extension Points
- MediaRotator modular design allows new APIs
- Encodarr webhook pattern supports additional notifications
- Script template enables new automation workflows

This primer provides the essential context needed to understand, troubleshoot, and extend the MediaCycler system effectively.
