#!/usr/bin/env bash
set -euo pipefail

# DUNO 360 — IONOS VPS bootstrap (Ubuntu 24.04)
# Usage on the server (as root):
#   sudo bash deploy/setup_ionos.sh
#
# Prerequisites:
#   1) Clone repo to /opt/duno360/app
#   2) Fill /opt/duno360/.env from deploy/production.env.example
#   3) Point duno360.com A-record to this server's public IP

APP_USER="duno360"
APP_GROUP="www-data"
APP_DIR="/opt/duno360/app"
ENV_FILE="/opt/duno360/.env"
SERVICE_NAME="duno360"
PYTHON_BIN="/usr/bin/python3"
DOMAIN="${DOMAIN:-duno360.com}"
VPS_IP="${VPS_IP:-217.160.36.235}"

echo "[1/9] Installing system packages (Ubuntu 24.04)..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y \
  python3 python3-venv python3-pip python3-dev \
  nginx git build-essential libpq-dev ufw curl certbot

echo "[2/9] Preparing app directories..."
id -u "${APP_USER}" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "${APP_USER}"
mkdir -p /opt/duno360 /var/log/duno360
touch /var/log/duno360/gunicorn-access.log /var/log/duno360/gunicorn-error.log
chown -R "${APP_USER}:${APP_GROUP}" /opt/duno360 /var/log/duno360
chmod -R 775 /var/log/duno360

if [[ ! -f "${APP_DIR}/manage.py" ]]; then
  echo "Clone the repository into ${APP_DIR} first:"
  echo "  git clone https://github.com/EspenQueston/book-project.git ${APP_DIR}"
  exit 1
fi

echo "[3/9] Creating virtual environment..."
if [[ ! -d "${APP_DIR}/.venv" ]]; then
  sudo -u "${APP_USER}" "${PYTHON_BIN}" -m venv "${APP_DIR}/.venv"
fi

echo "[4/9] Installing Python dependencies..."
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install --upgrade pip wheel
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install 'kkiapay>=0.0.6' --no-deps

echo "[5/9] Environment file..."
if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${APP_DIR}/deploy/production.env.example" "${ENV_FILE}"
  chown "${APP_USER}:${APP_GROUP}" "${ENV_FILE}"
  chmod 640 "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Edit it with real secrets, then re-run from step [8]."
  exit 0
fi
ln -sf "${ENV_FILE}" "${APP_DIR}/.env"

echo "[6/9] Writing systemd service..."
cat >/etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=DUNO 360 Django service (IONOS)
After=network.target

[Service]
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}
Environment=HOME=/opt/duno360
EnvironmentFile=${ENV_FILE}
ExecStart=${APP_DIR}/.venv/bin/gunicorn book_Project.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 120 --access-logfile /var/log/duno360/gunicorn-access.log --error-logfile /var/log/duno360/gunicorn-error.log
Restart=always
RestartSec=5
KillSignal=SIGQUIT
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
NoNewPrivileges=true
ReadWritePaths=${APP_DIR} /opt/duno360 /tmp /var/log/duno360

[Install]
WantedBy=multi-user.target
EOF

echo "[7/9] Writing nginx site..."
cat >/etc/nginx/sites-available/${SERVICE_NAME} <<EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN} ${VPS_IP};

    client_max_body_size 100M;

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
    }

    location /media/ {
        alias ${APP_DIR}/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/${SERVICE_NAME}
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo "[8/9] Django migrate + collectstatic..."
sudo -u "${APP_USER}" bash -c "cd ${APP_DIR} && set -a && source ${ENV_FILE} && set +a && .venv/bin/python manage.py migrate --noinput && .venv/bin/python manage.py collectstatic --noinput"

echo "[9/9] Enabling services..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

echo "Done. Site should respond on http://${VPS_IP}/"
echo "Next: certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
