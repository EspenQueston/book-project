#!/usr/bin/env bash
# Apply Django migrations to Supabase production (run on IONOS VPS as root).
# Usage:
#   bash /opt/duno360/app/deploy/migrate_supabase_production.sh
set -euo pipefail

APP_DIR="/opt/duno360/app"
ENV_FILE="/opt/duno360/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}" >&2
  exit 1
fi

echo "[1/4] Pull latest code..."
sudo -u duno360 bash -lc "cd ${APP_DIR} && git -c safe.directory=${APP_DIR} pull origin main"

echo "[2/4] Check Django..."
sudo -u duno360 bash -lc "cd ${APP_DIR} && set -a && . ${ENV_FILE} && set +a && .venv/bin/python manage.py check"

echo "[3/4] Apply migrations to Supabase..."
sudo -u duno360 bash -lc "cd ${APP_DIR} && set -a && . ${ENV_FILE} && set +a && .venv/bin/python manage.py migrate --noinput"

echo "[4/4] Migration status (last entries):"
sudo -u duno360 bash -lc "cd ${APP_DIR} && set -a && . ${ENV_FILE} && set +a && .venv/bin/python manage.py showmigrations --plan" | tail -12

echo "Done. Restart app if needed: systemctl restart duno360"
