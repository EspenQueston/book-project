#!/usr/bin/env python3
"""SSH to production VPS: git pull, migrate, compilemessages, collectstatic, restart app.

Auth (pick one — never commit secrets):
  • Key (recommended): set DUNO360_SSH_KEY_PATH to your private key file (chmod 600).
  • Password: set DUNO360_ROOT_PASS (avoid echoing in shared logs).

Optional:
  DUNO360_VPS_HOST   default 159.203.186.103
  DUNO360_SSH_USER   default root
  DUNO360_APP_DIR    default /opt/duno360/app
  DUNO360_APP_USER   default duno360

Usage (PowerShell):
  $env:DUNO360_SSH_KEY_PATH = 'C:\\Users\\You\\.ssh\\duno360_ed25519'
  python deploy/remote_prod_update.py
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

    host = os.environ.get("DUNO360_VPS_HOST", "159.203.186.103").strip()
    ssh_user = os.environ.get("DUNO360_SSH_USER", "root").strip()
    app_dir = os.environ.get("DUNO360_APP_DIR", "/opt/duno360/app").strip()
    app_user = os.environ.get("DUNO360_APP_USER", "duno360").strip()
    key_path = os.environ.get("DUNO360_SSH_KEY_PATH", "").strip()
    pw = os.environ.get("DUNO360_ROOT_PASS", "").strip()

    if not key_path and not pw:
        print(
            "Set DUNO360_SSH_KEY_PATH (private key file) or DUNO360_ROOT_PASS in the environment.",
            file=sys.stderr,
        )
        return 2

    cmd = rf"""set -e
chown -R {app_user}:www-data {app_dir} || true
if ! command -v msgfmt >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq && apt-get install -y gettext
fi
sudo -u {app_user} bash -lc 'cd {app_dir} && git -c safe.directory={app_dir} fetch origin && git -c safe.directory={app_dir} pull origin main'
sudo -u {app_user} bash -lc 'cd {app_dir} && set -a && . /opt/duno360/.env && set +a && .venv/bin/python manage.py migrate --noinput && .venv/bin/python manage.py compilemessages -l en -l fr && .venv/bin/python manage.py collectstatic --noinput'
systemctl restart duno360
systemctl is-active duno360
"""

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kw: dict = {"hostname": host, "username": ssh_user, "timeout": 180}
    if key_path:
        if not os.path.isfile(key_path):
            print(f"SSH key file not found: {key_path}", file=sys.stderr)
            return 2
        connect_kw["key_filename"] = key_path
    else:
        connect_kw["password"] = pw

    client.connect(**connect_kw)
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
