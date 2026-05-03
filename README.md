# Book Project Platform

A full-stack Django commerce platform combining book sales, marketplace products/courses/supermarket, messaging, multilingual UI, and vendor operations.

## Current Scope

- Public storefront for books and marketplace items
- Vendor center with dashboard, inventory tools, orders hub, and customer messaging
- Admin panel for catalog, vendors, users, orders, blog, and translations
- Unified order lifecycle across book and marketplace channels
- EN/FR/ZH localization workflow with server-side and client-side translation support

## Core Modules

- `manager/` — user-facing bookstore flows, vendor center, messaging, checkout, order management
- `marketplace/` — products, courses, supermarket items, variants, marketplace orders
- `core/` — shared services and application utilities
- `locale/` — translation resources

## Key Features

### Vendor Experience
- Unified vendor dashboard with cross-channel performance metrics (books/products/courses/supermarket)
- Order hub with filtering by channel and order type
- Detailed order pages with editable order/payment status
- Vendor-managed marketplace inventory: products, courses, supermarket items

### Commerce
- Cart/checkout and order tracking
- Shipping and customer contact update workflows
- Variant/attribute support for marketplace line items

### Localization
- Django i18n locale files (`locale/en`, `locale/fr`)
- Front-end translation dictionary in `manager/static/js/admin_i18n.js`

## Tech Stack

- Python / Django
- PostgreSQL (recommended)
- Bootstrap + Vanilla JS
- Pillow for media/image handling

## Quick Start

```bash
# 1) Create and activate virtualenv (Windows example)
python -m venv .venv
.venv\\Scripts\\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Configure env
copy .env.example .env
# then edit .env values

# 4) Apply migrations
python manage.py migrate

# 5) Run
python manage.py runserver
```

## Useful Commands

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py check
python manage.py seed_book_categories
```

## Security Notes

- Never commit secrets (`.env`, keys, credentials)
- Keep `DEBUG=False` in production
- Restrict media upload/storage permissions

## Deployment Notes

- Main branch: `main`
- This repository is configured for cPanel-style deployment assets (`.cpanel.yml`, `passenger_wsgi.py`)
- DigitalOcean production bootstrap script: `deploy/setup_digitalocean.sh`
- Production env template: `deploy/production.env.example`

## Production (DigitalOcean + Supabase)

1. Provision an Ubuntu VPS and point your domain A-record to the server IP.
2. Clone this repository to `/opt/duno360/app`.
3. Run:

```bash
sudo bash deploy/setup_digitalocean.sh
```

4. Fill `/opt/duno360/.env` (from `deploy/production.env.example`) with **real secret values**.
5. Restart services:

```bash
sudo systemctl restart duno360
sudo systemctl restart nginx
```

6. Enable HTTPS (recommended: Certbot), then keep `DEBUG=False`.

### Supabase database notes

- Use `DATABASE_URL` with `sslmode=require`.
- URL-encode passwords if they contain special characters.
- Keep database passwords and admin credentials out of git.
- Never expose service-role or private keys in frontend code.

## Maintenance Checklist

- Run migrations after pulling latest changes
- Rebuild/refresh translations after content updates
- Validate vendor dashboard and order update flows after schema changes

---

If you are onboarding a new developer, start with `manager/views.py`, `marketplace/views.py`, and the templates under `manager/templates/public/` and `marketplace/templates/marketplace/vendor/`.
