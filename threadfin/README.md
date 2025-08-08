# Threadfin

## Overview
Threadfin is a Docker-deployed IPTV proxy service that provides M3U playlist and XMLTV EPG (Electronic Program Guide) functionality for live TV streaming integration.

- **Purpose**: IPTV proxy and EPG service for media server integration  
- **Integration**: Compatible with Plex, Jellyfin, and IPTV client applications
- **Status**: Production-ready containerized deployment

## Features
IPTV streaming and proxy capabilities:
- **M3U Playlist Generation**: Create and manage IPTV channel playlists
- **XMLTV EPG Support**: Electronic Program Guide for channel scheduling
- **Multi-Source Aggregation**: Combine multiple IPTV sources into unified streams
- **Stream Filtering**: Include/exclude channels based on configurable rules
- **Buffer Management**: Handle stream buffering and re-streaming
- **Web Interface**: Browser-based configuration and monitoring dashboard

## Architecture / How it works
Containerized IPTV proxy with persistent configuration:

### Core Components
- **Threadfin Service**: Main IPTV proxy and streaming engine
- **Web Interface**: Configuration dashboard accessible via browser
- **Configuration Storage**: Persistent settings in `./data/conf/` directory
- **Buffer Management**: Temporary stream buffering in `./data/temp/`

### Data Flow
1. **Source Configuration**: Define IPTV source URLs and authentication
2. **Stream Aggregation**: Combine multiple sources into unified channel list
3. **Filtering Rules**: Apply channel inclusion/exclusion filters
4. **Playlist Generation**: Create M3U files for client consumption
5. **EPG Processing**: Generate XMLTV guide data
6. **Stream Proxy**: Handle client connections and re-stream content

### External Dependencies
- **Docker**: Containerization platform
- **IPTV Sources**: External streaming services and providers
- **Media Servers**: Plex, Jellyfin, or other IPTV-compatible clients

## Prerequisites
System requirements for IPTV proxy deployment:

### System Requirements
- **Operating System**: Linux with Docker support
- **Memory**: 1GB RAM minimum, 2GB recommended for multiple streams
- **Storage**: 10GB for configuration and temporary buffers
- **Network**: High-bandwidth connection for stream proxy operations

### Dependencies
```bash
# Docker installation
sudo apt update && sudo apt install -y docker.io docker-compose

# Verify Docker installation
docker --version
docker-compose --version
```

### API Keys & Credentials
- **IPTV Provider Credentials**: Source service authentication
- **Optional**: Reverse proxy SSL certificates for HTTPS access

## Installation

### Docker Deployment (Recommended)
```bash
# Navigate to Threadfin directory
cd threadfin

# Deploy with Docker Compose
docker-compose up -d

# Verify service is running
docker ps | grep threadfin
curl http://localhost:34400
```

### Manual Configuration
```bash
# Create configuration directories
mkdir -p threadfin/data/{conf,temp}
chmod 755 threadfin/data/{conf,temp}

# Set proper ownership for container
sudo chown -R 1000:1000 threadfin/data/
```

## Configuration

### Environment Variables
```bash
# Container Configuration
export PUID=1000                    # User ID for container
export PGID=1000                    # Group ID for container  
export TZ=America/New_York          # Timezone for scheduling

# Network Configuration  
export THREADFIN_PORT=34400         # Web interface and API port
```

### Docker Compose
```yaml
services:
  threadfin:
    image: fyb3roptik/threadfin
    container_name: threadfin
    ports:
      - 34400:34400
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=America/New_York
    volumes:
      - ./data/conf:/home/threadfin/conf
      - ./data/temp:/tmp/threadfin
    restart: unless-stopped
```

### Web Interface Configuration
1. **Access Dashboard**: Navigate to http://localhost:34400
2. **Initial Setup**: Complete wizard for basic configuration
3. **Source Management**: Add IPTV source URLs and credentials
4. **Filter Configuration**: Set channel filtering rules
5. **EPG Setup**: Configure Electronic Program Guide sources

### Configuration Files
Key configuration files in `./data/conf/`:
- **settings.json**: Main Threadfin settings and preferences
- **authentication.json**: User authentication configuration
- **urls.json**: IPTV source URLs and provider settings
- **pms.json**: Plex Media Server integration settings
- **xepg.json**: EPG source and mapping configuration

## Usage

### Basic Operations
```bash
# Start Threadfin service
cd threadfin
docker-compose up -d

# Access web interface
firefox http://localhost:34400

# View service logs
docker logs threadfin

# Restart service
docker-compose restart threadfin
```

### API Examples
```bash
# Get service status
curl http://localhost:34400/api/status

# Retrieve M3U playlist
curl http://localhost:34400/playlist.m3u8

# Get XMLTV EPG data
curl http://localhost:34400/xmltv.xml

# API endpoints (authentication required)
curl -H "Authorization: Bearer YOUR_API_TOKEN" \
  http://localhost:34400/api/channels
```

### Integration Examples
```bash
# Plex Live TV & DVR setup
# 1. In Plex Settings > Live TV & DVR
# 2. Add device: Network attached tuner
# 3. Use Threadfin IP: http://192.168.1.XXX:34400

# Jellyfin Live TV setup  
# 1. Dashboard > Plugins > Live TV
# 2. Add M3U Tuner: http://192.168.1.XXX:34400/playlist.m3u8
# 3. Add XMLTV Guide: http://192.168.1.XXX:34400/xmltv.xml
```

```python
# Python integration for automation
import requests

def get_threadfin_status():
    """Check Threadfin service status"""
    try:
        response = requests.get("http://localhost:34400/api/status", timeout=10)
        return response.status_code == 200
    except requests.RequestException:
        return False

def update_iptv_sources():
    """Update IPTV source configuration via API"""
    auth_token = "YOUR_THREADFIN_API_TOKEN" 
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Implementation depends on Threadfin API endpoints
    # Check web interface for available API calls
    pass

# Usage
if get_threadfin_status():
    print("Threadfin service is operational")
```

## Automation / Operations

### Automated Tasks
- **Stream Monitoring**: Continuous health checking of IPTV sources
- **EPG Updates**: Scheduled Electronic Program Guide refreshes
- **Playlist Generation**: Automatic M3U file updates
- **Buffer Management**: Temporary file cleanup and optimization

### Monitoring
```bash
# Service health check
curl -I http://localhost:34400

# Monitor container resource usage
docker stats threadfin

# Check active stream connections
docker logs threadfin | grep -i "stream\|connection"

# Verify configuration files
ls -la threadfin/data/conf/
```

### Backup Procedures
```bash
# Backup Threadfin configuration
tar -czf threadfin-config-$(date +%Y%m%d).tar.gz threadfin/data/conf/

# Backup Docker Compose setup
cp threadfin/docker-compose.yml threadfin/docker-compose.yml.backup

# Restore from backup
tar -xzf threadfin-config-YYYYMMDD.tar.gz
docker-compose up -d
```

## Troubleshooting

### Common Issues

#### Service won't start
**Symptoms**: Container exits, port binding failures
**Solutions**:
```bash
# Check port availability
sudo netstat -tulpn | grep :34400

# Verify volume permissions
ls -la threadfin/data/
sudo chown -R 1000:1000 threadfin/data/

# Check Docker logs
docker logs threadfin
```

#### Web interface not accessible
**Symptoms**: Connection refused, timeout errors
**Solutions**:
```bash
# Verify container is running
docker ps | grep threadfin

# Test local connectivity
curl -I http://localhost:34400

# Check firewall rules
sudo ufw status | grep 34400
```

#### IPTV streams not working
**Symptoms**: Channel loading failures, buffering issues
**Solutions**:
- Verify IPTV source URLs are accessible
- Check provider credentials and authentication
- Test streams directly outside Threadfin
- Review network bandwidth and connectivity

### Log Analysis
```bash
# Detailed container logs
docker logs -f threadfin

# Filter for specific issues
docker logs threadfin 2>&1 | grep -i "error\|fail\|timeout"

# Monitor stream activity
docker logs threadfin 2>&1 | grep -i "stream\|channel\|playlist"
```

### Debug Mode
```bash
# Run container in interactive mode for debugging
docker run -it --rm \
  -p 34400:34400 \
  -v $(pwd)/threadfin/data/conf:/home/threadfin/conf \
  -v $(pwd)/threadfin/data/temp:/tmp/threadfin \
  fyb3roptik/threadfin /bin/bash

# Enable verbose logging (if supported)
# Check Threadfin documentation for debug options
```

## Security

### Authentication
- **Web Interface**: Configure user authentication in settings
- **API Access**: Use API tokens for programmatic access
- **Network Security**: Restrict access to internal networks only

### Network Security
```bash
# Restrict access to internal networks
sudo ufw allow from 192.168.0.0/16 to any port 34400
sudo ufw deny 34400

# Use reverse proxy for SSL termination
# Configure nginx or Apache for HTTPS access
```

### Data Protection
- Configuration files contain IPTV provider credentials
- Temporary buffers may contain stream data
- Regular configuration backups recommended

### Security Best Practices
- Change default authentication credentials
- Use strong passwords for provider access  
- Monitor access logs for unauthorized usage
- Keep container images updated regularly

## Roadmap
Planned features and improvements:
- [ ] **Q1 2024**: Enhanced EPG data sources and mapping
- [ ] **Q2 2024**: Advanced stream filtering and categorization
- [ ] **Q3 2024**: Multi-tenant support for shared deployments
- [ ] **Q4 2024**: Integration with more media server platforms

## Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/threadfin-enhancement`  
3. Test changes with sample IPTV sources
4. Ensure Docker deployment remains functional
5. Document configuration changes
6. Submit a pull request with detailed description

Note: Threadfin is a third-party application. Direct contributions should be made to the upstream project repository.

### Development Setup
```bash
# Development environment for testing
docker pull fyb3roptik/threadfin:latest

# Test with sample configuration
mkdir -p test_threadfin/data/{conf,temp}
# Copy sample configuration files for testing
```

## License
Threadfin license: Check upstream project for licensing details.
MediaCycler integration: MIT License - see [LICENSE](../LICENSE) file.

---

## Acceptance Criteria
- [ ] Docker container starts successfully and binds to port 34400
- [ ] Web interface is accessible and responsive
- [ ] IPTV sources can be configured through web dashboard
- [ ] M3U playlist generation works correctly
- [ ] XMLTV EPG data is accessible via HTTP endpoints
- [ ] Configuration persists between container restarts
- [ ] Integration with Plex/Jellyfin functions as expected
- [ ] Service handles multiple concurrent stream connections
- [ ] Backup and restore procedures preserve functionality
- [ ] Logs provide sufficient detail for troubleshooting
