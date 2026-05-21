"""Shared SSH connection helper for production VPS maintenance scripts."""
from __future__ import annotations

import os
import sys


def connect_vps(timeout: int = 120):
    """Connect using DUNO360_SSH_KEY (preferred) or DUNO360_ROOT_PASS."""
    try:
        import paramiko
    except ImportError as exc:
        raise SystemExit("Install paramiko: pip install paramiko") from exc

    host = os.environ.get("DUNO360_VPS_HOST", "142.93.45.77").strip()
    user = os.environ.get("DUNO360_SSH_USER", "root").strip()
    key_path = os.environ.get("DUNO360_SSH_KEY", "").strip()
    password = os.environ.get("DUNO360_ROOT_PASS", "").strip()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if key_path:
        if not os.path.isfile(key_path):
            print(f"SSH key file not found: {key_path}", file=sys.stderr)
            raise SystemExit(2)
        client.connect(host, username=user, key_filename=key_path, timeout=timeout)
    elif password:
        client.connect(host, username=user, password=password, timeout=timeout)
    else:
        print(
            "Set DUNO360_SSH_KEY (path to private key) or DUNO360_ROOT_PASS",
            file=sys.stderr,
        )
        raise SystemExit(2)

    return client, host
