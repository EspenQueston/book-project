#!/usr/bin/env python3
"""
Push local translations to production DB via SSH + SFTP.

Usage:
  $env:DUNO360_ROOT_PASS = 'password'
  python deploy/sync_translations_prod.py

1. First run: python deploy/gen_prod_translation_script.py
   (generates deploy/apply_translations_prod.py with current local values)
2. Then run this script to upload + execute it on the VPS.
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

    script_path = os.path.join(os.path.dirname(__file__), "apply_translations_prod.py")
    if not os.path.exists(script_path):
        print(f"Script not found: {script_path}", file=sys.stderr)
        print("Run: python deploy/gen_prod_translation_script.py first", file=sys.stderr)
        return 2

    remote_tmp = "/tmp/apply_translations_prod.py"

    print(f"Connecting to {host}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username="root", password=pw, timeout=60)

    # Send the script via stdin echo trick (avoids SFTP dependency)
    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()

    # Base64-encode to avoid any shell quoting issues
    import base64
    b64 = base64.b64encode(script_content.encode("utf-8")).decode("ascii")

    write_cmd = f"echo {b64} | base64 -d > {remote_tmp} && echo 'uploaded'"
    _, stdout_w, stderr_w = client.exec_command(write_cmd)
    out_w = stdout_w.read().decode("utf-8", errors="replace").strip()
    if out_w != "uploaded":
        print(f"Upload failed: {out_w}", file=sys.stderr)
        client.close()
        return 1
    print(f"Uploaded script -> {remote_tmp}")

    # Run via Django on the VPS — copy to app dir first so book_Project module is importable
    cmd = (
        "sudo -u duno360 bash -lc '"
        f"cp {remote_tmp} /opt/duno360/app/_apply_translations.py && "
        "cd /opt/duno360/app && "
        "set -a && . /opt/duno360/.env && set +a && "
        ".venv/bin/python _apply_translations.py; "
        "rm -f /opt/duno360/app/_apply_translations.py'"
    )

    _stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    print(out)
    if err.strip():
        print(err, file=sys.stderr)
    code = stdout.channel.recv_exit_status()

    # Cleanup
    client.exec_command(f"rm -f {remote_tmp}")
    client.close()

    if code == 0:
        print("\nTranslation sync to production successful.")
    else:
        print(f"\nSync failed with exit code {code}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
