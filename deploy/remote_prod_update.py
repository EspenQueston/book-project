#!/usr/bin/env python3
"""SSH to production VPS: git pull, migrate, restart gunicorn.

Usage (do not commit secrets):
  set DUNO360_ROOT_PASS=...   # Windows PowerShell: $env:DUNO360_ROOT_PASS='...'
  python deploy/remote_prod_update.py

Optional: DUNO360_VPS_HOST (default 159.203.186.103)
"""
from __future__ import annotations

import os
import sys


def main() -> int:
    try:
        import paramiko
    except ImportError:
        print("Install paramiko: pip install paramiko", file=sys.stderr)
        return 2

    pw = os.environ.get("DUNO360_ROOT_PASS", "").strip()
    if not pw:
        print("Set environment variable DUNO360_ROOT_PASS", file=sys.stderr)
        return 2
    host = os.environ.get("DUNO360_VPS_HOST", "159.203.186.103").strip()

    cmd = r"""set -e
sudo -u duno360 bash -lc 'cd /opt/duno360/app && git -c safe.directory=/opt/duno360/app fetch origin && git -c safe.directory=/opt/duno360/app pull origin main'
sudo -u duno360 bash -lc 'cd /opt/duno360/app && set -a && . /opt/duno360/.env && set +a && .venv/bin/python manage.py migrate --noinput'
systemctl restart duno360
systemctl is-active duno360
"""

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username="root", password=pw, timeout=60)
    _stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    code = stdout.channel.recv_exit_status()
    client.close()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
