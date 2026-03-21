#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

# Create default manager account if it doesn't exist
python manage.py shell -c "
from manager.models import Manager;
Manager.objects.filter(number='admin').exists() or Manager.objects.create(number='admin', password='admin123', name='Administrator')
"
