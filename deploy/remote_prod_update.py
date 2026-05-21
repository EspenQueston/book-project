#!/usr/bin/env python3
"""SSH to production VPS: git pull, migrate, collectstatic, restart gunicorn.

Usage (do not commit secrets):
  set DUNO360_SSH_KEY=C:\\Users\\you\\.ssh\\id_ed25519
  python deploy/remote_prod_update.py

Or password auth:
  set DUNO360_ROOT_PASS=...
  python deploy/remote_prod_update.py

Optional: DUNO360_VPS_HOST (default 142.93.45.77)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vps_client import connect_vps


def main() -> int:
    client, host = connect_vps(timeout=120)
    print(f"Connected to {host}")

    cmd = r"""set -e
chown -R duno360:www-data /opt/duno360/app || true
if ! command -v msgfmt >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq && apt-get install -y gettext
fi
sudo -u duno360 bash -lc 'cd /opt/duno360/app && git -c safe.directory=/opt/duno360/app fetch origin && git -c safe.directory=/opt/duno360/app checkout -- locale/en/LC_MESSAGES/django.mo locale/fr/LC_MESSAGES/django.mo 2>/dev/null || true && git -c safe.directory=/opt/duno360/app reset --hard HEAD && git -c safe.directory=/opt/duno360/app pull origin main'
sudo -u duno360 bash -lc 'cd /opt/duno360/app && set -a && . /opt/duno360/.env && set +a && .venv/bin/python manage.py migrate --noinput && .venv/bin/python manage.py collectstatic --noinput && .venv/bin/python manage.py compilemessages -l en -l fr'
systemctl restart duno360
systemctl is-active duno360
"""

    _stdin, stdout, stderr = client.exec_command(cmd, timeout=300)
    for line in iter(stdout.readline, ""):
        print(line, end="", flush=True)
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print(err, file=sys.stderr)
    code = stdout.channel.recv_exit_status()
    client.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
