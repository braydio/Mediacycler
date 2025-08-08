# Scripts

## Overview
Collection of utility scripts for automated media management, focusing on Jellyfin integration and genre-based organization.

- **Purpose**: Automated media server integration and metadata management
- **Integration**: Direct API integration with Jellyfin for tagging and collection management
- **Status**: Production-ready shell scripts with robust error handling

## Features
Jellyfin automation capabilities:
- **Genre Tagging**: Automatic genre assignment based on folder structure
- **Collection Management**: Create and maintain genre-based collections
- **Batch Processing**: Process multiple TV shows in single execution
- **API Integration**: Direct Jellyfin API communication with authentication
- **Error Handling**: Skip missing items with warning messages
- **Flexible Structure**: Support for nested genre/show directory layouts

## Architecture / How it works
Shell-based automation with API integration:

### Core Components
- **tag_tv_genres.sh**: Jellyfin TV genre tagging and collection automation

### Data Flow
1. **Library Discovery**: Query Jellyfin for TV library ID
2. **Folder Scanning**: Recursively scan media directory structure
3. **Genre Extraction**: Extract genre from parent directory names
4. **Item Lookup**: Search Jellyfin for matching TV series
5. **Metadata Update**: Apply genre tags to found items
6. **Collection Management**: Create or update genre-based collections

### External Dependencies
- **Jellyfin API**: Media server integration for metadata and collections
- **curl**: HTTP client for API requests
- **jq**: JSON parsing and manipulation
- **bash**: Shell script execution environment

## Prerequisites
System requirements for script automation:

### System Requirements
- **Operating System**: Linux with bash support
- **Memory**: Minimal RAM requirements for script execution
- **Storage**: Access to media directories (`/mnt/netstorage/Media/TV`)
- **Network**: HTTP access to Jellyfin server

### Dependencies
```bash
# System packages
sudo apt update && sudo apt install -y curl jq bash

# Verify installations
curl --version
jq --version
bash --version
```

### API Keys & Credentials
Required for Jellyfin integration:
- **JELLYFIN_API_KEY**: Media server API access token
- **JELLYFIN_URL**: Server URL (e.g., http://192.168.1.198:8097)

## Installation

### Direct Installation
```bash
# Navigate to scripts directory
cd scripts

# Make scripts executable
chmod +x *.sh

# Test connectivity
./tag_tv_genres.sh --dry-run
```

### Environment Setup
```bash
# Create configuration file
cat > ~/.jellyfin_config << EOF
JELLYFIN_URL="http://192.168.1.198:8097"
JELLYFIN_API_KEY="YOUR_JELLYFIN_API_KEY"
MEDIA_ROOT="/mnt/netstorage/Media/TV"
EOF

# Source configuration
source ~/.jellyfin_config
```

## Configuration

### Environment Variables
```bash
# Jellyfin Server Configuration
export JELLYFIN_URL="http://192.168.1.198:8097"
export JELLYFIN_API_KEY="YOUR_JELLYFIN_API_KEY"

# Media Directory Structure
export MEDIA_ROOT="/mnt/netstorage/Media/TV"

# Script Behavior
export DRY_RUN=false
export VERBOSE=false
```

### Directory Structure Requirements
Expected folder layout for genre tagging:
```
/mnt/netstorage/Media/TV/
├── Documentary/
│   ├── Nature Documentaries/
│   ├── History Channel Shows/
│   └── Science Programs/
├── Action/
│   ├── Action Series 1/
│   └── Action Series 2/
└── Comedy/
    ├── Sitcom 1/
    └── Sitcom 2/
```

### Script Configuration
```bash
# tag_tv_genres.sh configuration (edit script header)
JELLYFIN_URL="http://192.168.1.198:8097"
API_KEY="YOUR_JELLYFIN_API_KEY_HERE"
MEDIA_ROOT="/mnt/netstorage/Media/TV"
```

## Usage

### Basic Operations
```bash
# Run genre tagging for all shows
cd scripts
./tag_tv_genres.sh

# Dry run to preview changes
JELLYFIN_URL="http://192.168.1.198:8097" \
API_KEY="YOUR_API_KEY" \
./tag_tv_genres.sh --dry-run

# Verbose output for debugging
./tag_tv_genres.sh --verbose
```

### API Examples
```bash
# Manual Jellyfin API testing
export JELLYFIN_URL="http://192.168.1.198:8097"
export API_KEY="YOUR_JELLYFIN_API_KEY"

# Test API connectivity
curl -s -H "X-Emby-Token: $API_KEY" "$JELLYFIN_URL/System/Info" | jq '.ServerName'

# List all libraries
curl -s -H "X-Emby-Token: $API_KEY" "$JELLYFIN_URL/Library/SelectableMediaFolders" | jq '.Items[].Name'

# Search for specific show
SHOW_NAME="Example Show"
curl -s -H "X-Emby-Token: $API_KEY" \
  "$JELLYFIN_URL/Items?IncludeItemTypes=Series&SearchTerm=$(echo "$SHOW_NAME" | jq -sRr @uri)" | jq '.Items[0].Name'
```

### Integration Examples
```bash
# Wrapper script for cron execution
#!/bin/bash
# jellyfin_automation.sh

export JELLYFIN_URL="http://192.168.1.198:8097"
export API_KEY="$(cat ~/.jellyfin_api_key)"
export MEDIA_ROOT="/mnt/netstorage/Media/TV"

cd /path/to/scripts
./tag_tv_genres.sh 2>&1 | logger -t jellyfin-automation

# Add to crontab
echo "0 2 * * * /path/to/jellyfin_automation.sh" | crontab -
```

```python
# Python wrapper for script execution
import subprocess
import os

def run_genre_tagging():
    """Execute genre tagging script with error handling"""
    env = os.environ.copy()
    env.update({
        'JELLYFIN_URL': 'http://192.168.1.198:8097',
        'API_KEY': 'YOUR_JELLYFIN_API_KEY',
        'MEDIA_ROOT': '/mnt/netstorage/Media/TV'
    })
    
    try:
        result = subprocess.run(
            ['./scripts/tag_tv_genres.sh'],
            env=env,
            capture_output=True,
            text=True,
            timeout=600
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Genre tagging script timed out")
        return False

# Usage
success = run_genre_tagging()
print(f"Genre tagging completed: {success}")
```

## Automation / Operations

### Automated Tasks
- **Genre Classification**: Assign genre tags based on directory structure
- **Collection Creation**: Generate genre-specific collections automatically
- **Metadata Synchronization**: Update Jellyfin metadata based on file organization
- **Batch Processing**: Handle multiple shows in single script execution

### Monitoring
```bash
# Check script execution logs
tail -f /var/log/syslog | grep jellyfin-automation

# Verify genre assignments in Jellyfin
curl -s -H "X-Emby-Token: $API_KEY" \
  "$JELLYFIN_URL/Items?IncludeItemTypes=Series&Fields=Genres" | \
  jq '.Items[] | {Name: .Name, Genres: .Genres}'

# Count items by genre
curl -s -H "X-Emby-Token: $API_KEY" \
  "$JELLYFIN_URL/Items?IncludeItemTypes=Series&Fields=Genres" | \
  jq '.Items[].Genres[]' | sort | uniq -c
```

### Backup Procedures
```bash
# Backup script configuration
cp scripts/tag_tv_genres.sh scripts/tag_tv_genres.sh.backup

# Export Jellyfin collections before automation
curl -s -H "X-Emby-Token: $API_KEY" \
  "$JELLYFIN_URL/Collections" | \
  jq '.' > jellyfin_collections_backup.json

# Create script package
tar -czf scripts-backup-$(date +%Y%m%d).tar.gz scripts/
```

## Troubleshooting

### Common Issues

#### Jellyfin API connection fails
**Symptoms**: curl errors, authentication failures
**Solutions**:
```bash
# Verify API key format
echo "API Key length: ${#API_KEY}"

# Test basic connectivity
curl -I "$JELLYFIN_URL"

# Check API authentication
curl -s -H "X-Emby-Token: $API_KEY" "$JELLYFIN_URL/System/Info" | jq '.ServerName'
```

#### TV library not found
**Symptoms**: "Could not find 'TV' library ID" error
**Solutions**:
```bash
# List all available libraries
curl -s -H "X-Emby-Token: $API_KEY" \
  "$JELLYFIN_URL/Library/SelectableMediaFolders" | \
  jq '.Items[] | {Name: .Name, Id: .Id}'

# Modify script if library name is different
sed -i 's/select(.Name=="TV")/select(.Name=="Television")/' tag_tv_genres.sh
```

#### Shows not found in Jellyfin
**Symptoms**: "WARNING: 'ShowName' not found in Jellyfin library"
**Solutions**:
```bash
# Check media directory structure
find "$MEDIA_ROOT" -mindepth 2 -maxdepth 2 -type d | head -10

# Verify Jellyfin library scan status
curl -s -H "X-Emby-Token: $API_KEY" \
  "$JELLYFIN_URL/Library/VirtualFolders" | \
  jq '.[] | {Name: .Name, Locations: .Locations}'

# Manually trigger library scan
curl -X POST -H "X-Emby-Token: $API_KEY" \
  "$JELLYFIN_URL/Library/Refresh"
```

### Log Analysis
```bash
# Enable script debugging
bash -x scripts/tag_tv_genres.sh 2>&1 | tee debug_output.log

# Check curl request/response details
CURL_DEBUG=1 ./tag_tv_genres.sh

# Monitor API rate limiting
grep -i "rate\|limit\|throttle" debug_output.log
```

### Debug Mode
```bash
# Run with verbose curl output
export CURL_OPTS="-v"
./tag_tv_genres.sh

# Add debug logging to script
sed -i 's/curl -s/curl -v -s/' tag_tv_genres.sh

# Interactive debugging
bash -x tag_tv_genres.sh
```

## Security

### Authentication
- **API Keys**: Use dedicated Jellyfin API tokens with minimal permissions
- **Network Access**: Restrict script execution to trusted systems
- **Credential Storage**: Store API keys in protected files or environment variables

### Network Security
```bash
# Verify Jellyfin server accessibility
nmap -p 8097 192.168.1.198

# Use HTTPS if available
export JELLYFIN_URL="https://jellyfin.yourdomain.com"
```

### Data Protection
- Scripts only read media metadata, no sensitive content access
- API operations limited to genre and collection management
- No external data transmission beyond Jellyfin server communication

### Security Best Practices
- Regular API key rotation
- Minimal script permissions on media directories
- Monitor API access logs for unauthorized usage
- Use dedicated service account for script execution

## Roadmap
Planned features and improvements:
- [ ] **Q1 2024**: Multi-server support for distributed Jellyfin instances
- [ ] **Q2 2024**: Movie genre tagging support
- [ ] **Q3 2024**: Custom metadata field management
- [ ] **Q4 2024**: Web-based script configuration interface

## Contributing
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/scripts-enhancement`
3. Test changes with sample media directories
4. Ensure compatibility with different Jellyfin versions
5. Add error handling for new features
6. Submit a pull request with detailed description

### Development Setup
```bash
# Test environment setup
mkdir -p test_media/TV/Documentary/Test\ Show
mkdir -p test_media/TV/Action/Action\ Show

# Create test Jellyfin instance (Docker)
docker run -d --name jellyfin-test \
  -p 8096:8096 \
  -v test_media:/media \
  jellyfin/jellyfin:latest

# Test scripts against test instance
export JELLYFIN_URL="http://localhost:8096"
export MEDIA_ROOT="./test_media/TV"
```

## License
This project is licensed under the MIT License - see [LICENSE](../LICENSE) file for details.

---

## Acceptance Criteria
- [ ] Script successfully connects to Jellyfin API with provided credentials
- [ ] TV library is discovered and accessible through script
- [ ] Genre tags are applied based on directory structure
- [ ] Collections are created and populated correctly  
- [ ] Missing shows are skipped with appropriate warnings
- [ ] Script handles network errors and API failures gracefully
- [ ] Batch processing completes without interruption
- [ ] Log output provides sufficient detail for troubleshooting
- [ ] Script can be executed via cron for automation
- [ ] Documentation examples work as written
