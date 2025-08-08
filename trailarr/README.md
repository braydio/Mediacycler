# Trailarr

## Overview
Trailarr is a Docker-deployed trailer management service that automatically downloads and organizes movie and TV show trailers for integration with media server libraries.

- **Purpose**: Automated trailer acquisition and organization for media collections
- **Integration**: Compatible with Plex, Jellyfin, and other media server platforms
- **Status**: Production-ready containerized deployment

## Features
Trailer management automation:
- **Automatic Discovery**: Find and download trailers for existing media collections
- **Multi-Source Support**: Aggregate trailers from YouTube and other video platforms
- **Quality Selection**: Choose trailer resolution and format preferences  
- **Organization**: Organize trailers alongside corresponding media files
- **Metadata Integration**: Embed trailer information in media server libraries
- **Scheduled Updates**: Regular trailer refresh and new content discovery

## Architecture / How it works
Containerized service with persistent configuration and media access:

### Core Components
- **Trailarr Service**: Main trailer discovery and download engine
- **Configuration Storage**: Persistent settings in `./trailarr_data/` directory
- **Media Integration**: Direct access to movie and TV show directories
- **Web Interface**: Browser-based configuration and monitoring dashboard

### Data Flow
1. **Media Scanning**: Discover existing movies and TV shows in libraries
2. **Trailer Search**: Query video platforms for corresponding trailers
3. **Quality Filtering**: Select trailers based on resolution and format preferences
4. **Download Processing**: Retrieve trailer files and convert if necessary
5. **Organization**: Place trailers in appropriate directory structure
6. **Metadata Updates**: Update media server library information

### External Dependencies
- **Docker**: Containerization platform
- **YouTube API**: Primary source for trailer content
- **Media Directories**: Access to movie and TV show file structures
- **Media Servers**: Plex, Jellyfin integration for library updates

## Prerequisites
System requirements for trailer management:

### System Requirements
- **Operating System**: Linux with Docker support
- **Memory**: 1GB RAM minimum, 2GB recommended for processing
- **Storage**: Direct access to media storage paths
- **Network**: Internet connectivity for trailer downloads

### Dependencies
```bash
# Docker installation
sudo apt update && sudo apt install -y docker.io docker-compose

# Verify Docker installation
docker --version
docker-compose --version
```

### API Keys & Credentials
- **YouTube API Key**: For trailer discovery and download (optional)
- **Media Server Integration**: API tokens for library updates

## Installation

### Docker Deployment (Recommended)
```bash
# Navigate to Trailarr directory
cd trailarr

# Fix Docker Compose syntax (if needed)
# Note: Current config has typo "unles-stopped" -> "unless-stopped"
sed -i 's/unles-stopped/unless-stopped/' docker-compose.yml

# Add missing volume mappings
# Edit docker-compose.yml to complete volume mappings

# Deploy with Docker Compose
docker-compose up -d

# Verify service is running
docker ps | grep trailarr
curl http://localhost:7889
```

### Configuration Setup
```bash
# Create configuration directory
mkdir -p trailarr/trailarr_data
chmod 755 trailarr/trailarr_data

# Set proper ownership for container
sudo chown -R 1000:1000 trailarr/trailarr_data
```

## Configuration

### Environment Variables
```bash
# Container Configuration
export TZ=America/New_York          # Timezone for scheduling
export PUID=1000                    # User ID for file permissions
export PGID=1000                    # Group ID for file permissions

# Media Paths
export MOVIES_PATH="/mnt/netstorage/Media/Movies"
export TV_PATH="/mnt/netstorage/Media/TV"

# Service Configuration
export TRAILARR_PORT=7889           # Web interface port
```

### Docker Compose (Corrected)
```yaml
services:
    trailarr:
        image: nandyalu/trailarr:latest
        container_name: trailarr
        environment:
            - TZ=America/New_York
            - PUID=1000
            - PGID=1000
        ports:
            - 7889:7889
        volumes:
            - ./trailarr_data:/config
            - /mnt/netstorage/Media/Movies:/movies
            - /mnt/netstorage/Media/TV:/tv
        restart: unless-stopped
```

### Web Interface Configuration
1. **Access Dashboard**: Navigate to http://localhost:7889
2. **Initial Setup**: Complete wizard for basic preferences
3. **Media Directories**: Configure movie and TV show paths  
4. **Quality Settings**: Set preferred trailer resolution and format
5. **Update Schedule**: Configure automatic refresh intervals

## Usage

### Basic Operations
```bash
# Start Trailarr service
cd trailarr
docker-compose up -d

# Access web interface
firefox http://localhost:7889

# View service logs
docker logs trailarr

# Restart service after configuration changes
docker-compose restart trailarr
```

### API Examples
```bash
# Check service status
curl http://localhost:7889/api/status

# Trigger manual scan
curl -X POST http://localhost:7889/api/scan

# Get trailer statistics
curl http://localhost:7889/api/stats

# API endpoints (check web interface for available calls)
curl -H "Content-Type: application/json" \
  http://localhost:7889/api/trailers
```

### Integration Examples
```bash
# Plex integration
# 1. Ensure trailers are in movie/show directories
# 2. Plex should automatically detect trailer files
# 3. Check Settings > Agents for trailer inclusion

# Jellyfin integration
# 1. Trailers detected automatically when scanning libraries
# 2. Configure metadata providers to include local trailers
# 3. Use naming convention: movie-trailer.mp4
```

```python
# Python automation example
import requests
import json

def trigger_trailer_scan():
    """Trigger manual trailer scan via API"""
    try:
        response = requests.post("http://localhost:7889/api/scan", timeout=30)
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"Trailer scan failed: {e}")
        return False

def get_trailer_stats():
    """Get trailer collection statistics"""
    try:
        response = requests.get("http://localhost:7889/api/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException as e:
        print(f"Stats retrieval failed: {e}")
    return None

# Usage
success = trigger_trailer_scan()
stats = get_trailer_stats()
print(f"Scan triggered: {success}, Stats: {stats}")
```

## Automation / Operations

### Automated Tasks
- **Media Discovery**: Continuous scanning for new movies and TV shows
- **Trailer Downloads**: Automatic trailer acquisition for discovered content
- **Quality Management**: Upgrade trailers when better versions become available
- **Library Updates**: Refresh media server libraries after trailer additions

### Monitoring
```bash
# Service health check
curl -I http://localhost:7889

# Monitor container resource usage
docker stats trailarr

# Check download activity
docker logs trailarr | grep -i "download\|trailer\|complete"

# Verify trailer organization
find /mnt/netstorage/Media/Movies -name "*trailer*" -type f | head -10
find /mnt/netstorage/Media/TV -name "*trailer*" -type f | head -10
```

### Backup Procedures
```bash
# Backup Trailarr configuration
tar -czf trailarr-config-$(date +%Y%m%d).tar.gz trailarr/trailarr_data/

# Backup Docker Compose setup
cp trailarr/docker-compose.yml trailarr/docker-compose.yml.backup

# Restore from backup
tar -xzf trailarr-config-YYYYMMDD.tar.gz
docker-compose up -d
```

## Troubleshooting

### Common Issues

#### Service won't start
**Symptoms**: Container exits, configuration errors
**Solutions**:
```bash
# Check port availability
sudo netstat -tulpn | grep :7889

# Verify volume permissions
ls -la trailarr/trailarr_data/
sudo chown -R 1000:1000 trailarr/trailarr_data/

# Fix Docker Compose syntax errors
docker-compose config
```

#### Media directories not accessible
**Symptoms**: No movies/shows found, permission denied
**Solutions**:
```bash
# Verify volume mounts
docker inspect trailarr | grep -A 10 "Mounts"

# Check media directory permissions
ls -la /mnt/netstorage/Media/Movies/
ls -la /mnt/netstorage/Media/TV/

# Test directory access from container
docker exec trailarr ls -la /movies
docker exec trailarr ls -la /tv
```

#### Trailers not downloading
**Symptoms**: Discovery works but downloads fail
**Solutions**:
- Check internet connectivity from container
- Verify YouTube API quotas and limits
- Review quality and format settings
- Check storage space for trailer files

### Log Analysis
```bash
# Detailed container logs
docker logs -f trailarr

# Filter for download issues
docker logs trailarr 2>&1 | grep -i "error\|fail\|download"

# Monitor trailer processing
docker logs trailarr 2>&1 | grep -i "trailer\|process\|complete"
```

### Debug Mode
```bash
# Run container in interactive mode for debugging
docker run -it --rm \
  -p 7889:7889 \
  -v $(pwd)/trailarr/trailarr_data:/config \
  -v /mnt/netstorage/Media/Movies:/movies \
  -v /mnt/netstorage/Media/TV:/tv \
  nandyalu/trailarr:latest /bin/bash

# Check application logs within container
docker exec trailarr cat /config/logs/trailarr.log
```

## Security

### Authentication
- **Web Interface**: Configure user authentication if available
- **Network Access**: Restrict access to internal networks only
- **File System**: Container access limited to specified media directories

### Network Security
```bash
# Restrict access to internal networks
sudo ufw allow from 192.168.0.0/16 to any port 7889
sudo ufw deny 7889
```

### Data Protection
- Configuration may contain API keys and credentials
- Trailer files are publicly available content
- Regular configuration backups recommended

### Security Best Practices
- Use strong authentication for web interface
- Monitor download activity for unusual behavior
- Keep container images updated
- Restrict file system permissions appropriately

## Roadmap
Planned features and improvements:
- [ ] **Q1 2024**: Enhanced trailer quality selection algorithms
- [ ] **Q2 2024**: Support for additional video platforms beyond YouTube
- [ ] **Q3 2024**: Advanced organization and naming conventions
- [ ] **Q4 2024**: Integration with more media server platforms

## Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/trailarr-enhancement`
3. Test changes with sample media collections
4. Ensure Docker deployment remains functional
5. Document configuration changes
6. Submit a pull request with detailed description

Note: Trailarr is a third-party application. Direct contributions should be made to the upstream project repository.

### Development Setup
```bash
# Development environment for testing
docker pull nandyalu/trailarr:latest

# Create test media structure
mkdir -p test_media/{Movies,TV}
# Add sample movie and TV show directories for testing
```

## License
Trailarr license: Check upstream project for licensing details.
MediaCycler integration: MIT License - see [LICENSE](../LICENSE) file.

---

## Acceptance Criteria
- [ ] Docker container starts successfully and binds to port 7889
- [ ] Web interface is accessible and responsive
- [ ] Media directories are properly mounted and accessible
- [ ] Service discovers existing movies and TV shows
- [ ] Trailer downloads complete successfully
- [ ] Trailers are organized correctly in media directories
- [ ] Configuration persists between container restarts
- [ ] Integration with media servers functions as expected
- [ ] Backup and restore procedures preserve functionality
- [ ] Logs provide sufficient detail for troubleshooting
