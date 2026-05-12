#!/bin/bash
# =============================================================
# DUNO 360 — VPS bootstrap via DigitalOcean web console
# Paste this ENTIRE script in the DO console (Droplet → Console)
# =============================================================
set -e

APP_DIR="/opt/duno360/app"
APP_USER="duno360"
REPO="https://github.com/EspenQueston/book-project.git"
DOMAIN="duno360.com"

echo "===== [1] System packages ====="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends \
    nginx git python3.11 python3.11-venv python3.11-dev \
    python3-pip build-essential libpq-dev ufw curl openssl

echo "===== [2] App user + dirs ====="
id -u $APP_USER &>/dev/null || useradd --system --home $APP_DIR --shell /bin/bash $APP_USER
mkdir -p $APP_DIR /opt/duno360
chown -R $APP_USER:$APP_USER /opt/duno360

echo "===== [3] Clone repo ====="
if [ -d "$APP_DIR/.git" ]; then
    cd $APP_DIR && git pull
else
    git clone $REPO $APP_DIR
fi
chown -R $APP_USER:$APP_USER $APP_DIR

echo "===== [4] Python venv ====="
sudo -u $APP_USER python3.11 -m venv $APP_DIR/.venv
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install --upgrade --quiet pip wheel
sudo -u $APP_USER $APP_DIR/.venv/bin/pip install --quiet -r $APP_DIR/requirements.txt

echo "===== [5] Production .env ====="
cat > /opt/duno360/.env << 'ENVEOF'
# ⚠  Fill in real values before running!
DEBUG=False
SECRET_KEY=CHANGE_ME_generate_a_50char_random_string
ALLOWED_HOSTS=duno360.com,www.duno360.com,127.0.0.1,localhost
FORCE_HTTPS=True
DATABASE_URL=postgresql://postgres:YOUR_DB_PASSWORD@db.gebnxwsrezadwuvmqtyy.supabase.co:5432/postgres?sslmode=require
CSRF_TRUSTED_ORIGINS=https://duno360.com,https://www.duno360.com
KKIAPAY_PUBLIC_KEY=YOUR_KKIAPAY_PUBLIC_KEY
KKIAPAY_PRIVATE_KEY=YOUR_KKIAPAY_PRIVATE_KEY
KKIAPAY_SECRET=YOUR_KKIAPAY_SECRET
KKIAPAY_SANDBOX=False
KKIAPAY_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET
SUPABASE_S3_ACCESS_KEY=YOUR_S3_ACCESS_KEY
SUPABASE_S3_SECRET_KEY=YOUR_S3_SECRET_KEY
SUPABASE_S3_BUCKET=media
SUPABASE_S3_ENDPOINT=https://gebnxwsrezadwuvmqtyy.supabase.co/storage/v1/s3
NGROK_ENABLED=False
ENVEOF
chmod 600 /opt/duno360/.env
chown $APP_USER:$APP_USER /opt/duno360/.env
ln -sf /opt/duno360/.env $APP_DIR/.env

echo "===== [6] Django migrate + collectstatic ====="
PY="$APP_DIR/.venv/bin/python"
cd $APP_DIR
sudo -u $APP_USER $PY manage.py migrate --noinput
sudo -u $APP_USER $PY manage.py collectstatic --noinput --clear

echo "===== [7] Systemd service ====="
cat > /etc/systemd/system/duno360.service << 'SVCEOF'
[Unit]
Description=DUNO 360 Django App
After=network.target

[Service]
User=duno360
Group=duno360
WorkingDirectory=/opt/duno360/app
EnvironmentFile=/opt/duno360/.env
ExecStart=/opt/duno360/app/.venv/bin/gunicorn \
    --config /opt/duno360/app/gunicorn.conf.py \
    book_Project.wsgi:application
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable duno360
systemctl restart duno360

echo "===== [8] Self-signed TLS cert ====="
mkdir -p /etc/nginx/ssl
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/duno360.key \
    -out    /etc/nginx/ssl/duno360.crt \
    -subj "/CN=duno360.com/O=DUNO360/C=CG"
chmod 600 /etc/nginx/ssl/duno360.key

echo "===== [9] Nginx config ====="
cat > /etc/nginx/sites-available/duno360 << 'NGINXEOF'
server {
    listen 80;
    server_name duno360.com www.duno360.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name duno360.com www.duno360.com;

    ssl_certificate     /etc/nginx/ssl/duno360.crt;
    ssl_certificate_key /etc/nginx/ssl/duno360.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header Cross-Origin-Opener-Policy "same-origin-allow-popups" always;

    client_max_body_size 10M;

    location /static/ {
        alias /opt/duno360/app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, max-age=2592000";
    }

    location /media/ {
        alias /opt/duno360/app/media/;
        expires 7d;
    }

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/duno360 /etc/nginx/sites-enabled/duno360
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "===== [10] UFW firewall ====="
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "===== Done! Smoke test ====="
sleep 3
curl -sI http://127.0.0.1:8000/manager/ | head -3
systemctl status duno360 --no-pager -l | tail -10

echo ""
echo "✅ Setup complete — update Cloudflare DNS A record to 142.93.45.77"
