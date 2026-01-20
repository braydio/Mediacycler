#!/usr/bin/env bash
#
# Setup script for MediaCycler scheduled tasks
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEDIACYCLER_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔧 Setting up MediaCycler scheduled tasks..."

# Check if we're running as root or with sudo access
if [[ $EUID -eq 0 ]] || sudo -n true 2>/dev/null; then
    echo "✅ Running with appropriate permissions"
else
    echo "❌ This script requires sudo access to modify crontab"
    echo "Please run with: sudo $0"
    exit 1
fi

# Backup existing crontab
echo "📋 Backing up existing crontab..."
if crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null; then
    echo "✅ Crontab backed up to /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S)"
else
    echo "⚠️ No existing crontab to backup"
fi

# Create new cron entries
echo "⏰ Setting up cron jobs..."

# Get current crontab or create empty one
(crontab -l 2>/dev/null || echo "") | {
    # Remove any existing MediaCycler entries
    grep -v "MediaCycler" || true
    
    echo "# MediaCycler Scheduled Tasks"
    echo "# MediaRotator - runs every hour at minute 0"
    echo "0 * * * * cd $MEDIACYCLER_DIR && python mediarotator/media_rotator.py --add-limit 5 --movie-rotation-limit 2 --show-rotation-limit 1 >> logs/media_rotator.log 2>&1"
    echo ""
    echo "# Media Health Check - runs daily at 2:00 AM"
    echo "# NOTE: Modify the MEDIA_DIR path in the script before enabling"
    echo "# 0 2 * * * cd $MEDIACYCLER_DIR && python encodarr/media_healthcheck.py >> logs/healthcheck.log 2>&1"
    echo ""
    echo "# Genre Tagging - runs weekly on Sunday at 3:00 AM"
    echo "# NOTE: Set JELLYFIN_API_KEY environment variable before enabling"
    echo "# 0 3 * * 0 cd $MEDIACYCLER_DIR && JELLYFIN_API_KEY=\$JELLYFIN_API_KEY scripts/tag_tv_genres.sh >> logs/genre_tagging.log 2>&1"
    echo ""
} | crontab -

echo "✅ Cron jobs installed successfully!"

# Create logs directory if it doesn't exist
mkdir -p "$MEDIACYCLER_DIR/logs"

echo "📁 Created logs directory: $MEDIACYCLER_DIR/logs"

echo ""
echo "🔍 Current crontab entries:"
crontab -l | grep -A 10 -B 2 "MediaCycler"

echo ""
echo "📝 Next steps:"
echo "1. Review the cron jobs with: crontab -e"
echo "2. Enable the commented health check and genre tagging jobs if desired"
echo "3. Set required environment variables in your shell profile:"
echo "   - RADARR_API_KEY"
echo "   - SONARR_API_KEY" 
echo "   - JELLYFIN_API_KEY (for genre tagging)"
echo "4. Test MediaRotator manually first:"
echo "   cd $MEDIACYCLER_DIR && python mediarotator/media_rotator.py --dry-run"

echo ""
echo "✅ Setup complete! MediaRotator will now run hourly."
