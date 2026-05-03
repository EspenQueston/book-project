#!/usr/bin/env bash
# =============================================================================
# DUNO 360 - DigitalOcean VPS Initial Setup Script
# Run as root on the VPS: bash deploy_vps.sh
# =============================================================================
set -euo pipefail

APP_DIR="/var/www/duno360"
REPO="https://github.com/EspenQueston/book-project.git"
PYTHON="python3.11"

echo "==> Updating system packages..."
apt-get update -qq && apt-get upgrade -y -qq

echo "==> Installing dependencies..."
apt-get install -y -qq \
    python3.11 python3.11-venv python3.11-dev \
    python3-pip nginx git curl \
    libpq-dev build-essential \
    certbot python3-certbot-nginx

echo "==> Creating app user and directories..."
id -u www-data &>/dev/null || useradd -r -s /bin/false www-data
mkdir -p "$APP_DIR" /var/log/duno360
chown www-data:www-data /var/log/duno360

echo "==> Cloning / updating repository..."
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR"
    sudo -u www-data git pull origin main
else
    git clone "$REPO" "$APP_DIR"
    chown -R www-data:www-data "$APP_DIR"
fi

echo "==> Setting up Python virtual environment..."
cd "$APP_DIR"
[ -d venv ] || $PYTHON -m venv venv
source venv/bin/activate

echo "==> Installing Python requirements..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "==> Checking .env file..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo ""
    echo "  *** .env file not found! ***"
    echo "  Create $APP_DIR/.env with the following content"
    echo "  (replace placeholders with real values):"
    echo ""
    echo "  DEBUG=False"
    echo "  SECRET_KEY=<generate with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\">"
    echo "  ALLOWED_HOSTS=159.203.186.103,scholarquest.tech,www.scholarquest.tech"
    echo "  DATABASE_URL=postgresql://postgres:<DB-PASSWORD>@db.gebnxwsrezadwuvmqtyy.supabase.co:5432/postgres"
    echo "  DJANGO_ADMIN_PASSWORD=<strong-password>"
    echo "  EMAIL_HOST_USER=espen@profitexb2b.com"
    echo "  EMAIL_HOST_PASSWORD=<email-password>"
    echo "  CSRF_TRUSTED_ORIGINS=http://159.203.186.103,https://scholarquest.tech,https://www.scholarquest.tech"
    echo ""
    echo "  After creating .env, re-run this script."
    exit 1
fi

echo "==> Running Django setup (collectstatic, migrate, admin)..."
bash build.sh

echo "==> Installing systemd service..."
cp duno360.service /etc/systemd/system/duno360.service
systemctl daemon-reload
systemctl enable duno360
systemctl restart duno360

echo "==> Configuring Nginx..."
cp nginx.conf.example /etc/nginx/sites-available/duno360
ln -sf /etc/nginx/sites-available/duno360 /etc/nginx/sites-enabled/duno360
# Disable default site if present
[ -L /etc/nginx/sites-enabled/default ] && rm /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ""
echo "======================================================"
echo "  Deployment complete!"
echo "  Site: http://159.203.186.103"
echo "  To get HTTPS (recommended):"
echo "    certbot --nginx -d scholarquest.tech -d www.scholarquest.tech"
echo "======================================================"
