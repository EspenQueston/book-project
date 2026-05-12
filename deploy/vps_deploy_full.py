"""
DUNO 360 - Full VPS Deployment via Paramiko (password auth, long banner timeout)
Run: python deploy/vps_deploy_full.py

This script:
1. Connects to VPS via password auth (bypasses SSH key issue)
2. Adds laptop SSH key to authorized_keys (so future deploys use key auth)
3. Installs all Python deps
4. Runs Django migrate + collectstatic
5. Installs Cloudflare Origin Certificate
6. Configures Nginx
7. Starts/restarts all services
"""
import os
import paramiko
import time
import sys

# ── VPS CONFIG ────────────────────────────────────────────────────────────────
HOST     = os.environ.get("VPS_HOST", "142.93.45.77")
USER     = os.environ.get("VPS_USER", "root")
PASSWORD = os.environ.get("VPS_PASSWORD", "")
if not PASSWORD:
    sys.exit("ERROR: VPS_PASSWORD environment variable is required. Set it before running this script.")

# SSH key to add to authorized_keys (your laptop key)
LAPTOP_PUBKEY = os.environ.get("LAPTOP_SSH_PUBKEY", "")
if not LAPTOP_PUBKEY:
    sys.exit("ERROR: LAPTOP_SSH_PUBKEY environment variable is required. Set it before running this script.")

# ── CLOUDFLARE CERT ───────────────────────────────────────────────────────────
# Read certificate files from local directory if they exist, otherwise require env vars
script_dir = os.path.dirname(os.path.abspath(__file__))
cf_crt_path = os.path.join(script_dir, "cloudflare_origin.crt")
cf_key_path = os.path.join(script_dir, "cloudflare_origin.key")

if os.path.exists(cf_crt_path) and os.path.exists(cf_key_path):
    with open(cf_crt_path, 'r') as f:
        CF_CERT = f.read()
    with open(cf_key_path, 'r') as f:
        CF_KEY = f.read()
else:
    CF_CERT = os.environ.get("CLOUDFLARE_CERT", "")
    CF_KEY = os.environ.get("CLOUDFLARE_KEY", "")
    if not CF_CERT or not CF_KEY:
        sys.exit("ERROR: Cloudflare certificate required. Either place cloudflare_origin.crt and cloudflare_origin.key in deploy/ directory, or set CLOUDFLARE_CERT and CLOUDFLARE_KEY environment variables.")

# ── NGINX CONFIG ──────────────────────────────────────────────────────────────
NGINX_CONF = """server {
    listen 80;
    server_name duno360.com www.duno360.com;
    return 301 https://duno360.com$request_uri;
}

server {
    listen 443 ssl http2;
    server_name duno360.com www.duno360.com;

    ssl_certificate     /etc/ssl/cloudflare/duno360.com.pem;
    ssl_certificate_key /etc/ssl/cloudflare/duno360.com.key;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
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
"""

# ── SYSTEMD SERVICE ───────────────────────────────────────────────────────────
SYSTEMD_SERVICE = """[Unit]
Description=DUNO 360 Gunicorn
After=network.target

[Service]
User=duno360
Group=duno360
WorkingDirectory=/opt/duno360/app
EnvironmentFile=/opt/duno360/.env
ExecStart=/opt/duno360/app/.venv/bin/gunicorn book_Project.wsgi:application \\
    --bind 0.0.0.0:8000 \\
    --workers 3 \\
    --timeout 120 \\
    --access-logfile /opt/duno360/logs/access.log \\
    --error-logfile /opt/duno360/logs/error.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

# ── HELPERS ───────────────────────────────────────────────────────────────────
def run(client, cmd, timeout=120, check=True):
    print(f"\n>>> {cmd[:100]}{'...' if len(cmd)>100 else ''}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    if out:
        print(out[-2000:])  # last 2000 chars to avoid flooding
    if err and code != 0:
        print(f"[STDERR] {err[-1000:]}")
    if check and code != 0:
        print(f"[EXIT {code}] Command failed.")
        sys.exit(1)
    return out, err, code

def write_file(sftp, path, content, mode=0o644):
    """Write a string to a remote file via SFTP."""
    import io
    print(f"    Writing {path} ...")
    with sftp.open(path, "w") as f:
        f.write(content)
    sftp.chmod(path, mode)

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("DUNO 360 - Full VPS Deployment")
    print(f"Target: {USER}@{HOST}")
    print("=" * 60)

    # Connect with long timeouts to handle slow SSH banner
    print("\n[1/8] Connecting to VPS (may take up to 120s if server is busy)...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for attempt in range(1, 4):
        try:
            client.connect(
                HOST,
                username=USER,
                password=PASSWORD,
                look_for_keys=False,   # skip key auth, use password directly
                allow_agent=False,
                banner_timeout=120,
                auth_timeout=60,
                timeout=120,
            )
            print("    Connected!")
            break
        except Exception as e:
            print(f"    Attempt {attempt}/3 failed: {e}")
            if attempt == 3:
                print("\nERROR: Cannot connect. Use the DigitalOcean web console instead.")
                sys.exit(1)
            time.sleep(10)

    sftp = client.open_sftp()

    # ── Step 2: Add SSH key to authorized_keys ────────────────────────────────
    print("\n[2/8] Adding laptop SSH key to authorized_keys...")
    run(client, "mkdir -p /root/.ssh && chmod 700 /root/.ssh")
    run(client, f"""
grep -qxF '{LAPTOP_PUBKEY}' /root/.ssh/authorized_keys 2>/dev/null || \
echo '{LAPTOP_PUBKEY}' >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
""")
    print("    SSH key added - future logins will use key auth!")

    # ── Step 3: Update code ───────────────────────────────────────────────────
    print("\n[3/8] Pulling latest code from GitHub...")
    run(client, "cd /opt/duno360/app && git fetch origin && git reset --hard origin/main")

    # ── Step 4: Install Python deps ───────────────────────────────────────────
    print("\n[4/8] Installing Python dependencies (this takes 2-4 minutes)...")
    run(client,
        "sudo -u duno360 /opt/duno360/app/.venv/bin/pip install --upgrade pip wheel --quiet",
        timeout=120)
    run(client,
        "sudo -u duno360 /opt/duno360/app/.venv/bin/pip install -r /opt/duno360/app/requirements.txt --quiet",
        timeout=600)

    # ── Step 5: Django setup ──────────────────────────────────────────────────
    print("\n[5/8] Running Django migrate + collectstatic...")
    run(client, "cd /opt/duno360/app && sudo -u duno360 .venv/bin/python manage.py migrate --noinput", timeout=120)
    run(client, "cd /opt/duno360/app && sudo -u duno360 .venv/bin/python manage.py collectstatic --noinput --clear", timeout=120)

    # ── Step 6: Cloudflare Origin Certificate ─────────────────────────────────
    print("\n[6/8] Installing Cloudflare Origin Certificate...")
    run(client, "mkdir -p /etc/ssl/cloudflare")
    write_file(sftp, "/etc/ssl/cloudflare/duno360.com.pem", CF_CERT, mode=0o644)
    write_file(sftp, "/etc/ssl/cloudflare/duno360.com.key", CF_KEY, mode=0o600)

    # ── Step 7: Nginx config ──────────────────────────────────────────────────
    print("\n[7/8] Configuring Nginx...")
    write_file(sftp, "/etc/nginx/sites-available/duno360", NGINX_CONF, mode=0o644)
    run(client, "ln -sf /etc/nginx/sites-available/duno360 /etc/nginx/sites-enabled/duno360")
    run(client, "rm -f /etc/nginx/sites-enabled/default")
    run(client, "nginx -t", check=False)
    run(client, "systemctl reload nginx")

    # ── Step 8: Restart app service ───────────────────────────────────────────
    print("\n[8/8] Restarting duno360 service...")
    run(client, "systemctl daemon-reload")
    run(client, "systemctl restart duno360")
    time.sleep(5)

    # Final status check
    print("\n" + "=" * 60)
    print("FINAL STATUS CHECK")
    print("=" * 60)
    out, _, _ = run(client, "systemctl is-active duno360", check=False)
    print(f"  Service status: {out.strip()}")

    out, _, _ = run(client, "curl -sI http://127.0.0.1:8000/manager/ 2>/dev/null | head -3", check=False)
    print(f"  Gunicorn test:\n{out}")

    out, _, _ = run(client, "curl -sk https://127.0.0.1/manager/ -o /dev/null -w '%{http_code}' 2>/dev/null", check=False)
    print(f"  Nginx HTTPS test: {out.strip()}")

    run(client, "journalctl -u duno360 -n 10 --no-pager", check=False)

    sftp.close()
    client.close()
    print("\n" + "=" * 60)
    print("DEPLOYMENT COMPLETE!")
    print(f"  Site: https://duno360.com/manager/")
    print("  Next: Set Cloudflare SSL mode to 'Full (strict)'")
    print("        at https://dash.cloudflare.com → SSL/TLS → Overview")
    print("=" * 60)

if __name__ == "__main__":
    main()
