#!/bin/bash
# =============================================================
# DUNO 360 — IONOS VPS bootstrap (paste in IONOS/KVM console)
# Ubuntu 24.04 · Host: 217.160.36.235
# =============================================================
set -e

APP_DIR="/opt/duno360/app"
APP_USER="duno360"
REPO="https://github.com/EspenQueston/book-project.git"
DOMAIN="duno360.com"
VPS_IP="217.160.36.235"

echo "===== [1] System packages ====="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
    nginx git python3 python3-venv python3-dev \
    python3-pip build-essential libpq-dev ufw curl openssl certbot

echo "===== [2] App user + dirs ====="
id -u $APP_USER &>/dev/null || useradd --system --home $APP_DIR --shell /bin/bash $APP_USER
mkdir -p $APP_DIR /opt/duno360 /var/log/duno360
chown -R $APP_USER:www-data /opt/duno360 /var/log/duno360

echo "===== [3] Clone repo ====="
if [ -d "$APP_DIR/.git" ]; then
    cd $APP_DIR && git pull
else
    git clone $REPO $APP_DIR
fi

echo "===== [4] Python venv + deps ====="
sudo -u $APP_USER python3 -m venv $APP_DIR/.venv
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install --upgrade pip wheel
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install -r $APP_DIR/requirements.txt

echo "===== [5] .env skeleton ====="
if [ ! -f /opt/duno360/.env ]; then
    cp $APP_DIR/deploy/production.env.example /opt/duno360/.env
    chmod 640 /opt/duno360/.env
    chown $APP_USER:www-data /opt/duno360/.env
    echo ">>> Edit /opt/duno360/.env with production secrets, then run:"
    echo "    bash $APP_DIR/deploy/setup_ionos.sh"
    exit 0
fi
ln -sf /opt/duno360/.env $APP_DIR/.env

echo "===== [6] Run full setup ====="
bash $APP_DIR/deploy/setup_ionos.sh

echo "✅ Bootstrap complete — verify: curl -I http://${VPS_IP}/"
