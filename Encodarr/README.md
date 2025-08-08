# Encodarr

## Overview
Encodarr is a Flask-based transcoding notification service that receives webhook notifications about media files requiring transcoding and automatically processes them using architecture-specific scripts.

- **Purpose**: Automated media transcoding triggered by external notifications
- **Integration**: Webhook endpoint for media servers and content management systems
- **Status**: Production-ready with Pi/x86 architecture auto-detection

## Features
Transcoding automation capabilities:
- **Webhook API**: RESTful endpoint for transcode notifications (`/notify`)
- **Architecture Detection**: Automatic Pi vs x86 system detection in transcode scripts
- **Logging System**: Comprehensive transcode operation logging
- **Containerized Deployment**: Docker-based deployment with volume mounting
- **Media Format Support**: Handles various video/audio codec combinations
- **Error Handling**: Robust error reporting and timeout management

## Architecture / How it works
Flask web service with external script execution:

### Core Components
- **app.py**: Flask application with `/notify` webhook endpoint
- **transcode.sh**: System-specific transcoding script with architecture detection
- **media_healthcheck.py**: Media file corruption detection utility
- **media_transcode.py**: Batch transcoding for Pi-incompatible codecs

### Data Flow
1. External system sends POST to `/notify` endpoint with file metadata
2. Flask app logs incoming request with video/audio codec information
3. Transcode script executes with file path parameter
4. System architecture detected (Pi vs Arch/x86) for appropriate processing
5. Transcoding results logged to alerts log file
6. HTTP 200 response returned to caller

### External Dependencies
- **Docker**: Containerized execution environment
- **FFmpeg**: Media analysis and transcoding engine
- **File System**: Direct access to media storage paths

## Prerequisites
System and deployment requirements:

### System Requirements
- **Operating System**: Linux with Docker support
- **Memory**: 2GB RAM minimum, 4GB recommended for 4K content
- **Storage**: Access to media storage paths (`/mnt/netstorage/Media`)
- **Network**: HTTP access on port 8099

### Dependencies
```bash
# System packages (if running without Docker)
sudo apt update && sudo apt install -y python3 python3-pip python3-venv ffmpeg

# Python packages
pip install flask

# Docker deployment (recommended)
sudo apt install -y docker.io docker-compose
```

### API Keys & Credentials
- No external API keys required
- File system access permissions needed for media paths

## Installation

### Docker Deployment (Recommended)
```bash
# Navigate to Encodarr directory
cd Encodarr

# Build and deploy container
docker-compose up -d

# Verify service is running
curl http://localhost:8099/notify -I
# Should return: 405 Method Not Allowed (correct for GET request)
```

### Manual Installation
```bash
# Create Python environment
cd Encodarr
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask

# Make transcode script executable
chmod +x transcode.sh

# Start service
python3 app.py
```

## Configuration

### Environment Variables
```bash
# Flask Configuration
export FLASK_HOST="0.0.0.0"
export FLASK_PORT="8099"
export FLASK_DEBUG="false"

# Transcoding Paths
export ALERTS_LOG="/app/alerts_log.log"
export TRANSCODE_SCRIPT="/app/transcode.sh"

# Media Storage
export MEDIA_ROOT="/mnt/netstorage/Media"
export TRANSCODED_OUTPUT="/mnt/netstorage/Media/Transcoded"
```

### Docker Compose
```yaml
services:
  transcode_notifier:
    build: .
    container_name: transcode_notifier
    ports:
      - "8099:8099"
    volumes:
      - /home/pi:/app/host_home_pi           # Pi user access
      - /mnt/netstorage:/mnt/netstorage      # Media storage
    environment:
      - TZ=America/New_York
    restart: unless-stopped
```

### Dockerfile Configuration
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x transcode.sh

EXPOSE 8099
CMD ["python", "app.py"]
```

## Usage

### Basic Operations
```bash
# Check service status
curl http://localhost:8099/notify -I

# View service logs
docker logs transcode_notifier

# Monitor alerts log
docker exec transcode_notifier tail -f /app/alerts_log.log
```

### API Examples
```bash
# Send transcoding notification
curl -X POST http://localhost:8099/notify \
  -H "Content-Type: application/json" \
  -d '{
    "file": "/mnt/netstorage/Media/Movies/Example.mkv",
    "video": "h265",
    "audio": "ac3"
  }'

# Example with different codecs
curl -X POST http://localhost:8099/notify \
  -H "Content-Type: application/json" \
  -d '{
    "file": "/mnt/netstorage/Media/TV/Series/S01E01.mkv", 
    "video": "h264",
    "audio": "aac"
  }'
```

### Integration Examples
```python
import requests
import json

def notify_transcode(file_path, video_codec, audio_codec):
    """Send transcoding notification to Encodarr"""
    url = "http://localhost:8099/notify"
    payload = {
        "file": file_path,
        "video": video_codec,
        "audio": audio_codec
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"Transcode notification failed: {e}")
        return False

# Usage example
success = notify_transcode(
    "/mnt/netstorage/Media/Movies/movie.mkv",
    "h265",
    "ac3"
)
```

```bash
# Shell script integration
#!/bin/bash
notify_transcode() {
    local file="$1"
    local video="$2" 
    local audio="$3"
    
    curl -s -X POST http://localhost:8099/notify \
        -H "Content-Type: application/json" \
        -d "{\"file\": \"$file\", \"video\": \"$video\", \"audio\": \"$audio\"}" \
        > /dev/null
}

# Usage
notify_transcode "/path/to/file.mkv" "h265" "ac3"
```

## Automation / Operations

### Automated Tasks
- **Real-time Processing**: Immediate response to webhook notifications
- **Architecture Detection**: Automatic Pi vs x86 transcode strategy selection
- **Log Rotation**: Automatic alerts log management
- **Error Recovery**: Timeout handling and failure logging

### Monitoring
```bash
# Health check endpoint
curl http://localhost:8099/notify -I

# Check container status
docker ps | grep transcode_notifier

# Monitor resource usage
docker stats transcode_notifier

# View recent transcode activities
docker exec transcode_notifier tail -20 /app/alerts_log.log
```

### Backup Procedures
```bash
# Backup alerts log
docker cp transcode_notifier:/app/alerts_log.log ./alerts_log.backup

# Backup configuration
tar -czf encodarr-config-$(date +%Y%m%d).tar.gz \
    docker-compose.yml \
    Dockerfile \
    app.py \
    transcode.sh

# Restore configuration
tar -xzf encodarr-config-YYYYMMDD.tar.gz
docker-compose up -d --build
```

## Troubleshooting

### Common Issues

#### Service won't start
**Symptoms**: Container exits immediately, port binding errors
**Solutions**:
```bash
# Check port availability
sudo netstat -tulpn | grep :8099

# Verify Docker permissions
sudo usermod -aG docker $USER && newgrp docker

# Check container logs
docker logs transcode_notifier
```

#### Transcode script fails
**Symptoms**: HTTP 200 but no transcode output, script errors in logs
**Solutions**:
```bash
# Verify script permissions
docker exec transcode_notifier ls -la /app/transcode.sh

# Test script manually
docker exec -it transcode_notifier /app/transcode.sh "/path/to/test/file.mkv"

# Check FFmpeg availability
docker exec transcode_notifier which ffmpeg
```

#### File path not accessible
**Symptoms**: File not found errors, permission denied in transcode logs
**Solutions**:
```bash
# Verify volume mounts
docker inspect transcode_notifier | grep -A 10 "Mounts"

# Check file permissions
ls -la /mnt/netstorage/Media/

# Test path access from container
docker exec transcode_notifier ls -la /mnt/netstorage/Media/
```

### Log Analysis
```bash
# Error patterns in alerts log
docker exec transcode_notifier grep -i "error\|fail" /app/alerts_log.log

# Successful transcodes
docker exec transcode_notifier grep -i "transcode output" /app/alerts_log.log

# Processing time analysis
docker exec transcode_notifier grep -o "timeout\|completed" /app/alerts_log.log | sort | uniq -c
```

### Debug Mode
```bash
# Enable Flask debug mode
export FLASK_DEBUG=1
cd Encodarr && python3 app.py

# Run transcode script manually with verbose output
./transcode.sh "/path/to/test/file.mkv" 2>&1 | tee debug.log

# Interactive container debugging
docker exec -it transcode_notifier /bin/bash
```

## Security

### Authentication
- **No Authentication**: Service currently accepts all POST requests to `/notify`
- **Network Access**: Restrict access via firewall rules or reverse proxy
- **File System**: Container runs with limited file system access

### Network Security
```bash
# Restrict access to internal networks only
sudo ufw allow from 192.168.0.0/16 to any port 8099
sudo ufw deny 8099
```

### Data Protection
- Alerts log contains file paths but no sensitive content
- Transcode operations use read-only access to source files
- Transcoded output written to designated directory only

### Security Best Practices
- Regular container image updates
- Volume mounts with minimal required permissions
- Monitor alerts log for unauthorized access attempts
- Consider adding API key authentication for production use

## Roadmap
Planned features and improvements:
- [ ] **Q1 2024**: API key authentication for webhook endpoint
- [ ] **Q2 2024**: Multiple transcode profile support
- [ ] **Q3 2024**: Web UI for monitoring and configuration
- [ ] **Q4 2024**: Advanced queuing and priority management

## Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/encodarr-enhancement`
3. Test changes with sample media files
4. Ensure Docker deployment still works
5. Add tests for new functionality
6. Submit a pull request with detailed description

### Development Setup
```bash
# Local development environment
python3 -m venv venv
source venv/bin/activate
pip install flask pytest

# Run tests
python -m pytest tests/

# Test with local Flask server
export FLASK_DEBUG=1
python app.py
```

## License
This project is licensed under the MIT License - see [LICENSE](../LICENSE) file for details.

---

## Acceptance Criteria
- [ ] Flask service starts successfully and binds to port 8099
- [ ] `/notify` endpoint accepts POST requests with JSON payloads
- [ ] Transcode script executes with provided file paths
- [ ] Architecture detection works on both Pi and x86 systems
- [ ] Alerts log captures all transcode operations and results
- [ ] Docker deployment works without manual intervention
- [ ] Volume mounts provide access to media storage paths
- [ ] Error handling manages timeouts and script failures gracefully
- [ ] Container restarts automatically on failure
- [ ] Log files are accessible for monitoring and debugging
