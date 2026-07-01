#!/usr/bin/env python3
"""Apply Django migrations to Supabase production from your PC.

Requires PRODUCTION_DATABASE_URL (Supabase Postgres URI), e.g.:
  postgresql://postgres:PASSWORD@db.<project-ref>.supabase.co:5432/postgres?sslmode=require

Windows PowerShell:
  $env:PRODUCTION_DATABASE_URL='postgresql://...'
  .\.venv\Scripts\python.exe deploy\migrate_supabase_local.py

Linux/macOS:
  export PRODUCTION_DATABASE_URL='postgresql://...'
  python deploy/migrate_supabase_local.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    db_url = os.environ.get("PRODUCTION_DATABASE_URL", "").strip()
    if not db_url:
        print("Set PRODUCTION_DATABASE_URL to your Supabase Postgres URI.", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[1]
    manage = root / "manage.py"
    if not manage.exists():
        print(f"manage.py not found at {manage}", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    for key in ("DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT"):
        env.pop(key, None)

    python = sys.executable
    venv_py = root / ".venv" / "Scripts" / "python.exe"
    if venv_py.exists():
        python = str(venv_py)

    print("Running Django migrate against Supabase production...")
    for cmd in (
        [python, str(manage), "check"],
        [python, str(manage), "migrate", "--noinput"],
        [python, str(manage), "showmigrations", "--plan"],
    ):
        print("\n$", " ".join(cmd))
        result = subprocess.run(cmd, cwd=str(root), env=env)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
