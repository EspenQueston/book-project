#!/bin/bash
# =============================================================================
# REMOTE VPS DEPLOYMENT SCRIPT
# This runs ON the VPS via SSH
# =============================================================================
set -e

PROJECT_PATH="/opt/duno360/app"
SERVICE_NAME="duno360.service"

echo "  [VPS] Pulling latest code..."
cd "$PROJECT_PATH"

# Check if git repo exists
if [ ! -d ".git" ]; then
    echo "  [VPS] ERROR: Not a git repo at $PROJECT_PATH"
    exit 1
fi

# Pull from GitHub
git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || {
    echo "  [VPS] git pull failed. Trying to fetch and reset..."
    git fetch origin
    git reset --hard origin/main 2>/dev/null || git reset --hard origin/master 2>/dev/null
}

echo "  [VPS] Code updated."

# Activate virtual environment and run collectstatic
echo ""
echo "  [VPS] Running collectstatic..."
source .venv/bin/activate
python manage.py collectstatic --noinput 2>/dev/null || echo "  [VPS] collectstatic skipped or failed"

# Restart the service
echo ""
echo "  [VPS] Restarting $SERVICE_NAME..."
sudo systemctl restart "$SERVICE_NAME"

echo ""
echo "  [VPS] Checking service status..."
sudo systemctl is-active "$SERVICE_NAME" && echo "  [VPS] Service is RUNNING" || echo "  [VPS] WARNING: Service status unknown"

echo ""
echo "  [VPS] Deployment complete!"
