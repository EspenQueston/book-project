#!/usr/bin/env python3
"""
fix_ssl.py - Fix HTTPS SSL certificate on duno360.com VPS
Run from the DigitalOcean console:
  curl -fsSL https://raw.githubusercontent.com/EspenQueston/book-project/main/deploy/fix_ssl.py | python3
"""
import os, subprocess, urllib.request, hashlib, re, time

# ── New Cloudflare Origin Certificate (generated 2026-05-10) ──────────────────
CERT = """\
-----BEGIN CERTIFICATE-----
MIIEojCCA4qgAwIBAgIUUYsYoBea8pkTVHwbLgYxb3KZ3TwwDQYJKoZIhvcNAQEL
BQAwgYsxCzAJBgNVBAYTAlVTMRkwFwYDVQQKExBDbG91ZEZsYXJlLCBJbmMuMTQw
MgYDVQQLEytDbG91ZEZsYXJlIE9yaWdpbiBTU0wgQ2VydGlmaWNhdGUgQXV0aG9y
aXR5MRYwFAYDVQQHEw1TYW4gRnJhbmNpc2NvMRMwEQYDVQQIEwpDYWxpZm9ybmlh
MB4XDTI2MDUxMDE5NDYwMFoXDTQxMDUwNjE5NDYwMFowYjEZMBcGA1UEChMQQ2xv
dWRGbGFyZSwgSW5jLjEdMBsGA1UECxMUQ2xvdWRGbGFyZSBPcmlnaW4gQ0ExJjAk
BgNVBAMTHUNsb3VkZmxhcmUgT3JpZ2luIENlcnRpZmljYXRlMIIBIjANBgkqhkiG
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
"""

KEY = """\
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
"""

NGINX_CONF = """\
# duno360.com - Nginx HTTPS with Cloudflare Origin Certificate
server {
    listen 80;
    server_name duno360.com www.duno360.com 159.203.186.103;
    return 301 https://duno360.com$request_uri;
}

server {
    listen 443 ssl;
    server_name duno360.com www.duno360.com;

    ssl_certificate     /etc/ssl/cloudflare/duno360.com.fullchain.pem;
    ssl_certificate_key /etc/ssl/cloudflare/duno360.com.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers off;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 1d;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;

    client_max_body_size 512M;

    location /static/ {
        alias /var/www/duno360/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /var/www/duno360/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass          http://127.0.0.1:8000;
        proxy_set_header    Host              $host;
        proxy_set_header    X-Real-IP         $remote_addr;
        proxy_set_header    X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header    X-Forwarded-Proto https;
        proxy_read_timeout  120s;
        proxy_connect_timeout 10s;
        proxy_buffering     off;
    }
}
"""

APP_DIR  = '/opt/duno360/app'
ENV_FILE = '/opt/duno360/.env'
SSL_DIR  = '/etc/ssl/cloudflare'
PYTHON   = f'{APP_DIR}/.venv/bin/python'
SERVICE  = 'duno360'

def run(cmd, check=False, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw)
    out = (r.stdout + r.stderr).strip()
    if out:
        print(out[:1000])
    return r

def step(title):
    print(f'\n{"="*50}')
    print(f'  {title}')
    print('='*50)

# ── 1. Fail2ban: unban this runner (console uses localhost, skip) ─────────────
step('1. Firewall / fail2ban')
run('ufw allow 80/tcp')
run('ufw allow 443/tcp')
run('ufw --force enable')
# Unban any banned IPs just in case
run('fail2ban-client unban --all 2>/dev/null || true')
print('Firewall OK')

# ── 2. Write certificate files ────────────────────────────────────────────────
step('2. Writing SSL certificate and key')
os.makedirs(SSL_DIR, exist_ok=True)
os.chmod(SSL_DIR, 0o700)

with open(f'{SSL_DIR}/duno360.com.pem', 'w') as f:
    f.write(CERT)
os.chmod(f'{SSL_DIR}/duno360.com.pem', 0o644)
print(f'Cert written: {len(CERT)} bytes')

with open(f'{SSL_DIR}/duno360.com.key', 'w') as f:
    f.write(KEY)
os.chmod(f'{SSL_DIR}/duno360.com.key', 0o600)
print(f'Key written: {len(KEY)} bytes')

# ── 3. Verify cert/key match ──────────────────────────────────────────────────
step('3. Verifying cert/key match')
c = subprocess.run(['openssl','x509','-noout','-modulus','-in',f'{SSL_DIR}/duno360.com.pem'], capture_output=True, text=True)
k = subprocess.run(['openssl','rsa','-noout','-modulus','-in',f'{SSL_DIR}/duno360.com.key'], capture_output=True, text=True)
cm = hashlib.md5(c.stdout.strip().encode()).hexdigest()
km = hashlib.md5(k.stdout.strip().encode()).hexdigest()
print(f'Cert modulus hash: {cm}')
print(f'Key  modulus hash: {km}')
if cm != km:
    print('❌ MISMATCH - cert and key do not match!')
    exit(1)
print('✅ Cert/Key MATCH')

# Show cert validity
info = subprocess.run(['openssl','x509','-noout','-subject','-dates','-in',f'{SSL_DIR}/duno360.com.pem'], capture_output=True, text=True)
print(info.stdout.strip())

# ── 4. Build fullchain (cert + Cloudflare RSA CA) ────────────────────────────
step('4. Building fullchain with Cloudflare RSA CA')
cert_file = 'duno360.com.pem'  # fallback
try:
    rsa_ca_url = 'https://developers.cloudflare.com/ssl/static/origin_ca_rsa_root.pem'
    rsa_ca = urllib.request.urlopen(rsa_ca_url, timeout=15).read().decode()
    fullchain = CERT + rsa_ca
    with open(f'{SSL_DIR}/duno360.com.fullchain.pem', 'w') as f:
        f.write(fullchain)
    os.chmod(f'{SSL_DIR}/duno360.com.fullchain.pem', 0o644)
    cert_file = 'duno360.com.fullchain.pem'
    print(f'✅ Fullchain written ({len(fullchain)} bytes) with Cloudflare RSA CA')
except Exception as e:
    print(f'Warning: Could not download CA ({e}), using cert only')
    # Copy pem as fullchain so nginx config stays consistent
    import shutil
    shutil.copy(f'{SSL_DIR}/duno360.com.pem', f'{SSL_DIR}/duno360.com.fullchain.pem')
    cert_file = 'duno360.com.fullchain.pem'

# ── 5. Write Nginx config ─────────────────────────────────────────────────────
step('5. Writing Nginx configuration')
nginx_conf_path = '/etc/nginx/sites-available/duno360'
with open(nginx_conf_path, 'w') as f:
    f.write(NGINX_CONF)

run('ln -sf /etc/nginx/sites-available/duno360 /etc/nginx/sites-enabled/duno360')
run('rm -f /etc/nginx/sites-enabled/default')

r = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
print(r.stdout + r.stderr)
if 'test is successful' not in r.stderr:
    print('❌ Nginx config test FAILED')
    print(r.stderr)
    exit(1)

subprocess.run(['systemctl', 'reload', 'nginx'])
print('✅ Nginx reloaded')

# ── 6. Update .env ─────────────────────────────────────────────────────────────
step('6. Updating .env')
with open(ENV_FILE) as f:
    env = f.read()

def set_env(content, key, value):
    pattern = rf'^{re.escape(key)}=.*$'
    line = f'{key}={value}'
    if re.search(pattern, content, re.MULTILINE):
        return re.sub(pattern, line, content, flags=re.MULTILINE)
    return content.rstrip('\n') + '\n' + line + '\n'

env = set_env(env, 'ALLOWED_HOSTS',        'duno360.com,www.duno360.com,159.203.186.103,localhost,127.0.0.1')
env = set_env(env, 'CSRF_TRUSTED_ORIGINS', 'https://duno360.com,https://www.duno360.com')
env = set_env(env, 'FORCE_HTTPS',          'True')

with open(ENV_FILE, 'w') as f:
    f.write(env)

for k in ('ALLOWED_HOSTS', 'CSRF_TRUSTED_ORIGINS', 'FORCE_HTTPS'):
    m = re.search(rf'^{k}=(.+)$', env, re.MULTILINE)
    print(f'  {k}={m.group(1) if m else "NOT SET"}')

# ── 7. Run Django migrations ──────────────────────────────────────────────────
step('7. Running Django migrations')
env_dict = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'book_Project.settings'}
# Load .env vars
for line in env.splitlines():
    if '=' in line and not line.startswith('#'):
        k2, _, v2 = line.partition('=')
        env_dict[k2.strip()] = v2.strip()

r = subprocess.run(
    [PYTHON, 'manage.py', 'migrate', '--run-syncdb'],
    capture_output=True, text=True, cwd=APP_DIR, env=env_dict
)
output = r.stdout + r.stderr
print(output[-2000:] if len(output) > 2000 else output)
if r.returncode != 0:
    print('Warning: migrations had errors (may be OK if already applied)')

# ── 8. Collectstatic ──────────────────────────────────────────────────────────
step('8. Collectstatic')
r = subprocess.run(
    [PYTHON, 'manage.py', 'collectstatic', '--noinput'],
    capture_output=True, text=True, cwd=APP_DIR, env=env_dict
)
print((r.stdout + r.stderr)[-500:])

# ── 9. Restart app service ────────────────────────────────────────────────────
step('9. Restarting app service')
subprocess.run(['systemctl', 'restart', SERVICE])
time.sleep(3)
r = subprocess.run(['systemctl', 'is-active', SERVICE], capture_output=True, text=True)
status = r.stdout.strip()
print(f'Service {SERVICE}: {status}')
if status != 'active':
    subprocess.run(['journalctl', '-u', SERVICE, '-n', '30', '--no-pager'])
    exit(1)

# ── 10. Test local response ───────────────────────────────────────────────────
step('10. Testing local HTTP response')
run('curl -s -o /dev/null -w "Local HTTP status: %{http_code}\\n" http://127.0.0.1:8000/manager/public/')
run('curl -s -o /dev/null -w "HTTPS status (via nginx): %{http_code}\\n" -k https://127.0.0.1/manager/public/')

print('\n' + '='*50)
print('✅ ALL DONE')
print('='*50)
print('\nFinal checklist:')
print('  1. Cloudflare DNS: A duno360.com → 159.203.186.103 (Proxied ON)')
print('  2. Cloudflare DNS: A www       → 159.203.186.103 (Proxied ON)')
print('  3. Cloudflare SSL/TLS → Full (strict)')
print('\nTest: https://duno360.com/manager/public/')
