#!/usr/bin/env bash
# =============================================================================
# DUNO 360 - Production Update Script
# Run on the VPS as root to pull latest code and restart services.
# =============================================================================
set -euo pipefail

APP_DIR="/var/www/duno360"
REPO="https://github.com/EspenQueston/book-project.git"

echo "==> Pulling latest code..."
cd "$APP_DIR"
sudo -u www-data git pull origin main

echo "==> Activating virtual environment..."
source "$APP_DIR/venv/bin/activate"

echo "==> Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running database migrations..."
python manage.py migrate

echo "==> Restarting Gunicorn..."
systemctl restart duno360

echo "==> Checking service status..."
systemctl is-active --quiet duno360 && echo "  ✓ duno360 is running" || echo "  ✗ duno360 failed to start"

echo ""
echo "======================================================"
echo "  Production update complete!"
echo "  $(date)"
echo "======================================================"
