#!/usr/bin/env bash
set -euo pipefail

# DUNO 360 - DigitalOcean Ubuntu bootstrap (no secrets embedded)
# Usage:
#   sudo bash deploy/setup_digitalocean.sh
#
# After script:
#  1) Put real env values in /opt/duno360/.env
#  2) Run: sudo systemctl restart duno360

APP_USER="duno360"
APP_GROUP="www-data"
APP_DIR="/opt/duno360/app"
ENV_FILE="/opt/duno360/.env"
SERVICE_NAME="duno360"
PYTHON_BIN="/usr/bin/python3"
DOMAIN="${DOMAIN:-_}"

echo "[1/8] Installing system packages..."
apt-get update -y
apt-get install -y python3 python3-venv python3-pip nginx git

echo "[2/8] Preparing app directories..."
id -u "${APP_USER}" >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin "${APP_USER}"
mkdir -p /opt/duno360
mkdir -p "${APP_DIR}"
mkdir -p /var/log/duno360
touch /var/log/duno360/gunicorn-access.log /var/log/duno360/gunicorn-error.log
chown -R "${APP_USER}:${APP_GROUP}" /opt/duno360
chown -R "${APP_USER}:${APP_GROUP}" /var/log/duno360
chmod -R 775 /var/log/duno360

if [[ ! -f "${APP_DIR}/manage.py" ]]; then
  echo "Clone your repository into ${APP_DIR} before continuing."
  echo "Example:"
  echo "  sudo -u ${APP_USER} git clone https://github.com/EspenQueston/book-project.git ${APP_DIR}"
  exit 1
fi

echo "[3/8] Creating virtual environment..."
if [[ ! -d "${APP_DIR}/.venv" ]]; then
  sudo -u "${APP_USER}" "${PYTHON_BIN}" -m venv "${APP_DIR}/.venv"
fi

echo "[4/8] Installing Python dependencies..."
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install --upgrade pip
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

echo "[5/8] Environment file template..."
if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${APP_DIR}/deploy/production.env.example" "${ENV_FILE}"
  chown "${APP_USER}:${APP_GROUP}" "${ENV_FILE}"
  chmod 640 "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Fill it with real production values before restart."
fi

echo "[6/8] Writing systemd service..."
cat >/etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=DUNO 360 Django service
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

echo "[7/8] Writing nginx site..."
cat >/etc/nginx/sites-available/${SERVICE_NAME} <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

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
    }
}
EOF

ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/${SERVICE_NAME}
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

echo "[8/8] Django migrate + collectstatic + service start..."
sudo -u "${APP_USER}" bash -c "cd ${APP_DIR} && set -a && source ${ENV_FILE} && set +a && .venv/bin/python manage.py migrate --noinput && .venv/bin/python manage.py collectstatic --noinput"
systemctl daemon-reload
systemctl enable ${SERVICE_NAME}
systemctl restart ${SERVICE_NAME}

echo "Done."
echo "Next recommended step: install HTTPS with Certbot and set DOMAIN env before rerunning nginx section."
