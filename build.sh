#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

# Create default admin account if not present
# Password is read from DJANGO_ADMIN_PASSWORD env var (must be set in production!)
python manage.py shell -c "
import os
from manager.models import Manager
if not Manager.objects.filter(number='admin').exists():
    pw = os.environ.get('DJANGO_ADMIN_PASSWORD', '')
    if not pw:
        print('WARNING: DJANGO_ADMIN_PASSWORD not set — admin account not created')
    else:
        Manager.objects.create(number='admin', password=pw, name='Administrator')
        print('Admin account created.')
"
