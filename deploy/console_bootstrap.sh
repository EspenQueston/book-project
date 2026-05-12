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
DEBUG=False
SECRET_KEY=r@)_*cGCrsA%O^KJVQSvbp&o!IMi=HJNS4mBQfr*f)%7C@eQfy
ALLOWED_HOSTS=duno360.com,www.duno360.com,127.0.0.1,localhost
FORCE_HTTPS=True
DATABASE_URL=postgresql://postgres:IRF5xLlAX75Ax%22ay@db.gebnxwsrezadwuvmqtyy.supabase.co:5432/postgres?sslmode=require
CSRF_TRUSTED_ORIGINS=https://duno360.com,https://www.duno360.com
KKIAPAY_PUBLIC_KEY=855c58403ef411f1bf4f9fabcaa86999
KKIAPAY_PRIVATE_KEY=tpk_855c7f513ef411f1bf4f9fabcaa86999
KKIAPAY_SECRET=tsk_855ca6603ef411f1bf4f9fabcaa86999
KKIAPAY_SANDBOX=False
KKIAPAY_WEBHOOK_SECRET=duno360
SUPABASE_S3_ACCESS_KEY=9bd35cb7a1dfc190de0e299c642b0506
SUPABASE_S3_SECRET_KEY=ff74475b65c616ab36f8de4605f3502c27637ce3f184edb416ff2f9dda7e454b
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

echo "===== [8] Cloudflare Origin TLS cert ====="
mkdir -p /etc/nginx/ssl
cat > /etc/nginx/ssl/duno360.crt << 'CERTEOF'
-----BEGIN CERTIFICATE-----
MIIEojCCA4qgAwIBAgIUUYsYoBea8pkTVHwbLgYxb3KZ3TwwDQYJKoZIhvcNAQEL
BQAwgYsxCzAJBgNVBAYTAlVTMRkwFwYDVQQKExBDbG91ZEZsYXJlLCBJbmMuMTQw
MgYDVQQLEytDbG91ZEZsYXJlIE9yaWdpbiBTU0wgQ2VydGlmaWNhdGUgQXV0aG9y
aXR5MRYwFAYDVQQHEw1TYW4gRnJhbmNpc2NvMRMwEQYDVQQIEwpDYWxpZm9ybmlh
MB4XDTI2MDUxMDE5NDYwMFoXDTQxMDUwNjE5NDYwMFowYjEZMBcGA1UEChMQQ2xv
dWRGbGFyZSwgSW5jLjEdMBsGA1UECxMUQ2xvdWRGbGFyZSBPcmlnaW4gQ0ExJjAk
BgNVBAMTHUNsb3VkRmxhcmUgT3JpZ2luIENlcnRpZmljYXRlMIIBIjANBgkqhkiG
9w0BAQEFAAOCAQ8AMIIBCgKCAQEA3WdGSBDO2dS3cYA0/tE/P7PoFPGY+z+otjbM
SzJxvR782KgqERBV9FROfBhPi6Pj+TS/Uog13fmWX43POxRMtaFQoWCUzCito89t
gsVGkEG75VseN90zcHbxj4ZBkcFyqI6QnErkonGOBUq6AYG2gU9JsI6fFuodTgP/
r/iBpzs0WKUVR6vndWrwJConNCBi/8UIjOUSEqJZpkReLZD46SBXzTCY0oRXntO2
PcmcJ9UrJXlh9c8AlG6FlogpIU3M1JefHY7fND1S/miFB6IvN6CnMwQCE7c8yCOU
0uB7eI84HpAuCAMkcyUN9C47Q/FfvvFE7KIV2rODRCaItkCIOwIDAQABo4IBJDCC
ASAwDgYDVR0PAQH/BAQDAgWgMB0GA1UdJQQWMBQGCCsGAQUFBwMCBggrBgEFBQcD
ATAMBgNVHRMBAf8EAjAAMB0GA1UdDgQWBBT+oEQOtIHbJoYYBEnS6fEVPeWWgTAf
BgNVHSMEGDAWgBQk6FNXXXw0QIep65TbuuEWePwppDBABggrBgEFBQcBAQQ0MDIw
MAYIKwYBBQUHMAGGJGh0dHA6Ly9vY3NwLmNsb3VkZmxhcmUuY29tL29yaWdpbl9j
YTAlBgNVHREEHjAcgg0qLmR1bm8zNjAuY29tggtkdW5vMzYwLmNvbTA4BgNVHR8E
MTAvMC2gK6AphidodHRwOi8vY3JsLmNsb3VkZmxhcmUuY29tL29yaWdpbl9jYS5j
cmwwDQYJKoZIhvcNAQELBQADggEBAJiA7lUKQuzg/ZT2o5sQvJ+ly+/WntwU9wbM
mul+CDPpyKfykw/NCF4FMVnUD6XVv9XHm+7RmepFZPp+R/Owr7S7EifjqKOc2NfS
Lr4YlCkFSj29K68ryAn7Uze7oN+1fHV6UV0eqy6Fgb4GEB9OOJV+N5O4Ziw28Zpd
2SwUsQIEyYIPHdOwv1L6inI3hG/bD9J+0DZywUf/I0x1RJSw8Ve7rwFXgqmCiBMu
34I0S87WS8MZB4jALw2+Mv5rjJPQ6MZ/XTyEgOE8+F8+vu8AAOmYuwn9hx/5wKhb
ehZ8gKvxGKSpn9O2UI7wdPCixbI6rAEJ3CqIjNhWpkcgac4h8XM=
-----END CERTIFICATE-----
CERTEOF

cat > /etc/nginx/ssl/duno360.key << 'KEYEOF'
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDdZ0ZIEM7Z1Ldx
gDT+0T8/s+gU8Zj7P6i2NsxLMnG9HvzYqCoREFX0VE58GE+Lo+P5NL9SiDXd+ZZf
jc87FEy1oVChYJTMKK2jz22CxUaQQbvlWx433TNwdvGPhkGRwXKojpCcSuSicY4F
SroBgbaBT0mwjp8W6h1OA/+v+IGnOzRYpRVHq+d1avAkKic0IGL/xQiM5RISolmm
RF4tkPjpIFfNMJjShFee07Y9yZwn1SsleWH1zwCUboWWiCkhTczUl58djt80PVL+
aIUHoi83oKczBAITtzzII5TS4Ht4jzgekC4IAyRzJQ30LjtD8V++8UTsohXas4NE
Joi2QIg7AgMBAAECggEAJzQUvUkAn5CrZNUbTS2XAfwksaSv/nkgshcU6JHHkwHM
Kr7oJ/pZBfjxpsaVOzgrc2KUKBSHWUVLC6NsGN140cZ9JP4Ziub/DBz8GqY83ulM
0IloWeL4q0bcchoHPTxgRZls4MfgISVzTNuVARRLUS1Nco5mfCO7SaeqnCmoJ4if
ZHLIvRWRWIFkFut/sxLiZizYWL7HY+byRJMs/Kf8jFn8VvDYA903dq+aN7pNT2Ug
dEVwwWngxFbyDN4Cel2RGfDD+9f//j2ztCkGpFGZhA6ogXCBF/N71N+2J/LsyJ0+
/lsaX5xquIXUOFt3vwmYd7YjWkWp11rikrnF/PdIRQKBgQDw2rmtbm5pRUPmHx0X
ZoVUZvB2Ge5gKFBQyqAJz0IQ8soJZ07P4zIjOkcS0yX14UCI4SPsZQc6c2uvdSq3
vph5GDf7cnq02MPsRhsn3mamsHJ94TOx9LZYhl/4x2UOebsaRaDU9BwmTzshkgXn
SernIbI1PJ9xspMVbA2GAqQoTQKBgQDrU21keevknOqGfRzjLzL3MIjOHAVUPiol
SEeWFDre6PfASVTuH8WNIgZWMqZGHCu9bPA2YHFs7xVsvaljp93f9nCEaAEkVy3e
HShGETbnfqDJMG+kvu2/fD7LUReKyYIHBg6w1E6JdtDQMnhFzX/1K+twnKbmiT4c
6b/ZRFI2pwKBgQCkAh0b9y3iK1NwGVHDBIHYFny5vzCuc+U1DrVp2KNBTUK8oodt
UmVqzZ1mOTgJNcivLLg8mhMQ/1Wd1egv1O6YzyAX7j2WdmD7vEVzoaM+8LoV88sy
69Nbdq1Vh9nNwKDi4/T/7fZZM+ytEHVKqO/3Ud+7FrvwPUyg8sJGtfe4pQKBgHzU
CFcgBW2DfzRP8Z7hTpuo9yi93GXPg/O6355QpNnRonoxbAfUeqpevhXDUEgocVtO
Ci4OApzSRf8krFHcnelLhGv374Mja4VC2jYws3sgxJF0TASL8vl8IqMfJOnN8ldf
czOBqxdoG2QVIY+FbrbS0VUvA6mOa5BSvh22DBZJAoGAYQKFozUbQBsYCnJtFcdK
UKsi8YgwHOnvnpPgNMd94IJTcdU2OzHoLRy7wd6h5whLNjKmEDg6x8jNkuCZYb4h
90HBBm/TmNIpReeLGFSfOT4iQ5EEUUiJ/JwM2PzK0Kqo41wcD1OdEqtMlANMJtjV
k6acdnjrhLPR0HkY5W+zY1c=
-----END PRIVATE KEY-----
KEYEOF
chmod 600 /etc/nginx/ssl/duno360.key
chmod 644 /etc/nginx/ssl/duno360.crt

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
