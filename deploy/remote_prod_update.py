#!/usr/bin/env python3
"""SSH to production VPS: git pull, migrate, collectstatic, compilemessages, restart.

Run **only on your machine**. Do not paste passwords or private keys into chat or commits.

Authentication (pick one):
  1) Key file (recommended):
       set DUNO360_SSH_KEY=C:\\path\\to\\id_rsa   # or ~/.ssh/duno360_deploy
       optional: set DUNO360_SSH_USER=root
  2) Password (legacy):
       set DUNO360_ROOT_PASS=...

Optional:
  DUNO360_VPS_HOST   (default 159.203.186.103)
  DUNO360_APP_DIR    (default /opt/duno360/app)
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
    app_dir = os.environ.get("DUNO360_APP_DIR", "/opt/duno360/app").strip()
    ssh_user = os.environ.get("DUNO360_SSH_USER", "root").strip()
    key_path = os.environ.get("DUNO360_SSH_KEY", "").strip()
    pw = os.environ.get("DUNO360_ROOT_PASS", "").strip()

    if not key_path and not pw:
        print(
            "Set DUNO360_SSH_KEY (path to private key) or DUNO360_ROOT_PASS in the environment.",
            file=sys.stderr,
        )
        return 2

    cmd = rf"""set -e
chown -R duno360:www-data /opt/duno360/app || true
if ! command -v msgfmt >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq && apt-get install -y gettext
fi
sudo -u duno360 bash -lc 'cd {app_dir} && git -c safe.directory={app_dir} fetch origin && git -c safe.directory={app_dir} pull origin main'
sudo -u duno360 bash -lc 'cd {app_dir} && set -a && . /opt/duno360/.env && set +a && .venv/bin/python manage.py migrate --noinput && .venv/bin/python manage.py collectstatic --noinput && .venv/bin/python manage.py compilemessages -l en -l fr'
systemctl restart duno360
systemctl is-active duno360
"""

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kw: dict = {"hostname": host, "username": ssh_user, "timeout": 120}
    if key_path:
        if not os.path.isfile(key_path):
            print(f"SSH key file not found: {key_path}", file=sys.stderr)
            return 2
        connect_kw["key_filename"] = key_path
    else:
        connect_kw["password"] = pw

    try:
        client.connect(**connect_kw)
    except paramiko.SSHException as e:
        print(f"SSH connection failed: {e}", file=sys.stderr)
        return 1

    try:
        _stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        print(out)
        if err.strip():
            print(err, file=sys.stderr)
        code = stdout.channel.recv_exit_status()
        return code
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
