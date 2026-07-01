#!/usr/bin/env bash
# =============================================================
# DUNO 360 — Production update: remove AI chatbot, add Tawk.to
# Run on the VPS as root:
#   bash /opt/duno360/app/deploy/update_prod_tawkto.sh
# Or pipe directly from GitHub:
#   curl -fsSL https://raw.githubusercontent.com/EspenQueston/book-project/main/deploy/update_prod_tawkto.sh | bash
# =============================================================
set -euo pipefail

APP_DIR="/opt/duno360/app"
ENV_FILE="/opt/duno360/.env"
VENV="$APP_DIR/.venv/bin/python"
SERVICE="duno360"
APP_USER="duno360"

echo "===> [1/7] Pull latest code from GitHub"
sudo -u "$APP_USER" bash -lc "
  cd $APP_DIR
  git -c safe.directory=$APP_DIR fetch origin
  git -c safe.directory=$APP_DIR reset --hard HEAD
  git -c safe.directory=$APP_DIR pull origin main
"

echo "===> [2/7] Apply database migrations (drops chatbot tables)"
sudo -u "$APP_USER" bash -lc "
  cd $APP_DIR
  set -a && . $ENV_FILE && set +a
  $VENV manage.py migrate --noinput
"

echo "===> [3/7] Collect static files"
sudo -u "$APP_USER" bash -lc "
  cd $APP_DIR
  set -a && . $ENV_FILE && set +a
  $VENV manage.py collectstatic --noinput
"

echo "===> [4/7] Compile translation messages"
sudo -u "$APP_USER" bash -lc "
  cd $APP_DIR
  set -a && . $ENV_FILE && set +a
  $VENV manage.py compilemessages -l en -l fr
" || echo "  (compilemessages skipped — gettext not installed)"

echo "===> [5/7] Add Tawk.to env vars to $ENV_FILE (if not already present)"
if ! grep -q "TAWKTO_PROPERTY_ID" "$ENV_FILE"; then
  cat >> "$ENV_FILE" <<'ENVEOF'

# Tawk.to Live Chat Widget
# Get these from: https://dashboard.tawk.to -> Administration -> Property Settings
TAWKTO_PROPERTY_ID=YOUR_PROPERTY_ID_HERE
TAWKTO_WIDGET_ID=default
ENVEOF
  echo "  Added TAWKTO_* vars to $ENV_FILE — edit the file to set real values."
  echo "  Run:  nano $ENV_FILE"
else
  echo "  TAWKTO_* vars already present in $ENV_FILE — skipping."
fi

echo "===> [6/7] Drop legacy chatbot tables directly (safe if migration already ran)"
sudo -u "$APP_USER" bash -lc "
  cd $APP_DIR
  set -a && . $ENV_FILE && set +a
  $VENV -c \"
import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'book_Project.settings'
django.setup()
from django.db import connection
with connection.cursor() as cur:
    for tbl in ('chat_message', 'chat_session', 'chatbot_config'):
        cur.execute(f'DROP TABLE IF EXISTS {tbl} CASCADE')
        print(f'  Dropped {tbl} (if existed)')
\"
"

echo "===> [7/7] Restart application service"
systemctl restart "$SERVICE"
systemctl is-active "$SERVICE" && echo "  Service $SERVICE is running OK." || echo "  WARNING: service may not be running — check: journalctl -u $SERVICE -n 50"

echo ""
echo "======================================================"
echo " Deployment complete!"
echo ""
echo " Next step — configure Tawk.to:"
echo "  1. Log in to https://dashboard.tawk.to"
echo "  2. Go to Administration → Property Settings"
echo "  3. Copy your Property ID and Widget ID"
echo "  4. Edit: nano $ENV_FILE"
echo "     Set: TAWKTO_PROPERTY_ID=<your-property-id>"
echo "          TAWKTO_WIDGET_ID=<your-widget-id>  (often '1abc...' or 'default')"
echo "  5. Run: systemctl restart $SERVICE"
echo "======================================================"
