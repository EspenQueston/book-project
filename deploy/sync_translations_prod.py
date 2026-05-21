#!/usr/bin/env python3
"""
Push local translations to production DB via SSH.

Usage:
  set DUNO360_SSH_KEY=C:\\Users\\you\\.ssh\\id_ed25519
  python deploy/sync_translations_prod.py

1. First run: python deploy/gen_prod_translation_script.py
   (generates deploy/apply_translations_prod.py with current local values)
2. Then run this script to upload + execute it on the VPS.
"""
from __future__ import annotations

import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vps_client import connect_vps


def main() -> int:
    script_path = os.path.join(os.path.dirname(__file__), "apply_translations_prod.py")
    if not os.path.exists(script_path):
        print(f"Script not found: {script_path}", file=sys.stderr)
        print("Run: python deploy/gen_prod_translation_script.py first", file=sys.stderr)
        return 2

    remote_tmp = "/tmp/apply_translations_prod.py"

    client, host = connect_vps(timeout=60)
    print(f"Connected to {host}")

    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()

    b64 = base64.b64encode(script_content.encode("utf-8")).decode("ascii")

    write_cmd = f"echo {b64} | base64 -d > {remote_tmp} && echo 'uploaded'"
    _, stdout_w, stderr_w = client.exec_command(write_cmd)
    out_w = stdout_w.read().decode("utf-8", errors="replace").strip()
    if out_w != "uploaded":
        print(f"Upload failed: {out_w}", file=sys.stderr)
        client.close()
        return 1
    print(f"Uploaded script -> {remote_tmp}")

    cmd = (
        "sudo -u duno360 bash -lc '"
        f"cp {remote_tmp} /opt/duno360/app/_apply_translations.py && "
        "cd /opt/duno360/app && "
        "set -a && . /opt/duno360/.env && set +a && "
        ".venv/bin/python _apply_translations.py; "
        "rm -f /opt/duno360/app/_apply_translations.py'"
    )

    _stdin, stdout, stderr = client.exec_command(cmd, timeout=120)
    for line in iter(stdout.readline, ""):
        print(line, end="", flush=True)
    err = stderr.read().decode("utf-8", errors="replace")
    if err.strip():
        print(err, file=sys.stderr)
    code = stdout.channel.recv_exit_status()

    client.exec_command(f"rm -f {remote_tmp}")
    client.close()

    if code == 0:
        print("\nTranslation sync to production successful.")
    else:
        print(f"\nSync failed with exit code {code}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
