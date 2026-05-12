#!/bin/bash
# =============================================================
# DUNO 360 — Full VPS setup script
# Run as root on a fresh Ubuntu 22.04 server.
# Usage: bash setup_vps.sh
# =============================================================
set -e

APP_DIR="/opt/duno360/app"
APP_USER="duno360"
REPO_URL="https://github.com/EspenQueston/book-project.git"
DOMAIN="duno360.com"
PYTHON_VERSION="python3.11"

echo "===== [1/10] Installing system packages ====="
apt-get update -qq
apt-get install -y \
    nginx git python3.11 python3.11-venv python3.11-dev python3-pip \
    build-essential libpq-dev ufw curl certbot

echo "===== [2/10] Creating app user & directory ====="
id -u "$APP_USER" &>/dev/null || useradd --system --home "$APP_DIR" --shell /bin/bash "$APP_USER"
mkdir -p "$APP_DIR"
chown -R "$APP_USER:$APP_USER" /opt/duno360

echo "===== [3/10] Cloning / updating repository ====="
if [ -d "$APP_DIR/.git" ]; then
    cd "$APP_DIR"
    sudo -u "$APP_USER" git pull
else
    sudo -u "$APP_USER" git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

echo "===== [4/10] Setting up Python virtualenv ====="
sudo -u "$APP_USER" $PYTHON_VERSION -m venv "$APP_DIR/.venv"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip wheel
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "===== [5/10] Writing .env file ====="
if [ ! -f /opt/duno360/.env ]; then
    echo "⚠️  /opt/duno360/.env not found — creating skeleton from .env.example"
    cp "$APP_DIR/.env.example" /opt/duno360/.env
    chmod 600 /opt/duno360/.env
    chown "$APP_USER:$APP_USER" /opt/duno360/.env
    echo ""
    echo ">>> STOP: Edit /opt/duno360/.env with real values, then re-run this script."
    exit 1
fi
# Symlink into app dir so Django picks it up
ln -sf /opt/duno360/.env "$APP_DIR/.env"

echo "===== [6/10] Running Django management commands ====="
cd "$APP_DIR"
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" manage.py migrate --noinput
sudo -u "$APP_USER" "$APP_DIR/.venv/bin/python" manage.py collectstatic --noinput

echo "===== [7/10] Creating systemd service ====="
cat > /etc/systemd/system/duno360.service << 'SYSTEMD_EOF'
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
SYSTEMD_EOF

systemctl daemon-reload
systemctl enable duno360
systemctl restart duno360

echo "===== [8/10] Installing TLS certificates ====="
SSL_CERT="/etc/nginx/ssl/duno360.crt"
SSL_KEY="/etc/nginx/ssl/duno360.key"
mkdir -p /etc/nginx/ssl

if [ ! -f "$SSL_CERT" ] || [ ! -f "$SSL_KEY" ]; then
    echo "⚠️  SSL certificate files not found at:"
    echo "     $SSL_CERT"
    echo "     $SSL_KEY"
    echo "  Place your Cloudflare Origin Certificate (PEM) at $SSL_CERT"
    echo "  and the matching private key at $SSL_KEY, then re-run nginx config step."
fi

echo "===== [9/10] Configuring Nginx ====="
cat > /etc/nginx/sites-available/duno360 << NGINX_EOF
# Redirect HTTP → HTTPS
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate     $SSL_CERT;
    ssl_certificate_key $SSL_KEY;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    # COOP / COEP for KKiaPay widget compatibility
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
        proxy_set_header   Host \$host;
        proxy_set_header   X-Real-IP \$remote_addr;
        proxy_set_header   X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }
}
NGINX_EOF

ln -sf /etc/nginx/sites-available/duno360 /etc/nginx/sites-enabled/duno360
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "===== [10/10] Configuring UFW firewall ====="
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo ""
echo "✅  Setup complete! Site should be live at https://$DOMAIN"
echo "    Check gunicorn: systemctl status duno360"
echo "    Check nginx:    systemctl status nginx"
echo "    App logs:       journalctl -u duno360 -f"
