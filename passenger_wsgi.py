"""
WSGI configuration for Django Book Management System
For LWS cPanel Deployment on scholarquest.tech

This file is used by Passenger (the WSGI server in cPanel) to serve your Django application.

IMPORTANT: Update the paths below with your actual cPanel username
Replace 'username' with your cPanel username (e.g., 'scholarq' or similar)
"""

import sys
import os

# ============================================================================
# CONFIGURATION - UPDATE THESE PATHS FOR YOUR CPANEL ACCOUNT
# ============================================================================

# Your cPanel username (CHANGE THIS!)
CPANEL_USERNAME = 'cp2603370p21'  # e.g., 'scholarq'

# Application root - full path to your Django project
# Format: /home/CPANEL_USERNAME/scholarquest.tech/book_Project
project_home = f'/home/{CPANEL_USERNAME}/scholarquest.tech/book_Project'

# Virtual environment path
# Format: /home/CPANEL_USERNAME/virtualenv/scholarquest.tech/3.X/bin/activate_this.py
venv_path = f'/home/{CPANEL_USERNAME}/virtualenv/scholarquest.tech/3.8/bin/activate_this.py'

# ============================================================================
# WSGI APPLICATION SETUP
# ============================================================================

# Add your project directory to the sys.path
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set Django settings module
os.environ['DJANGO_SETTINGS_MODULE'] = 'book_Project.settings'

# Load environment variables from .env file
from pathlib import Path
env_file = Path(project_home) / '.env'
if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)

# Activate virtual environment
try:
    with open(venv_path) as file_:
        exec(file_.read(), dict(__file__=venv_path))
except FileNotFoundError:
    # If activate_this.py doesn't exist, try alternative activation
    pass

# Import Django WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# ============================================================================
# DEPLOYMENT CHECKLIST
# ============================================================================
# Before deployment, ensure:
# 1. Update CPANEL_USERNAME above with your actual cPanel username
# 2. Create .env file with production database credentials
# 3. Run: python manage.py migrate
# 4. Run: python manage.py collectstatic --noinput
# 5. Set proper file permissions: chmod 755 passenger_wsgi.py
# 6. Upload payment QR codes to manager/static/payment_qr/
# 7. Test the site and check error logs if issues occur
