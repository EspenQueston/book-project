# DUNO 360 — Book & Marketplace Platform

Full-stack Django commerce platform for **DUNO 360**: bookstore, multi-vendor marketplace (products, courses, supermarket), payments, messaging, escrow, and trilingual public UI (Chinese / English / French).

**Production site:** [duno360.com](https://duno360.com)

---

## Platform Overview

| Area | Description |
|------|-------------|
| **Public storefront** | Books, marketplace catalog, product/course/supermarket detail pages, cart, checkout, order tracking |
| **Vendor center** | Dashboard, inventory, orders hub, customer messaging, marketplace listing management |
| **Admin panel** | Catalog, vendors, users, orders, blog, analytics, inventory, email/messages, AI chatbot config |
| **Marketplace** | Products with variants, bulk/wholesale pricing rules, courses with lessons, supermarket items |
| **Payments** | KKiaPay, PawaPay (Central Africa), MTN MoMo, Airtel Money, wallet top-up |
| **Communications** | Contact form, Zoho SMTP, admin email inbox, vendor/customer chat, Twilio SMS OTP at signup |

---

## Implemented Features

### Storefront & Content
- Public home, books, authors, publishers, blog, services, about, contact, legal/info pages
- Hero wave dividers and responsive layouts across key public pages
- FAQ section with full i18n (zh / en / fr)
- Official **DUNO 360** store badge and premium seller card styling
- Social links (Facebook, Instagram, TikTok, YouTube) in footer, contact, and blog
- Platform phone **+242 06 679 03 86** — direct calls and WhatsApp (footer, contact, support, order tracking)
- Product recommendations and live viewer counts (Redis-backed when configured)
- Reviews, wishlist, publisher/vendor follow, Congo location selectors for checkout

### Marketplace & Catalog
- Products, courses, supermarket items with images stored on Supabase/S3-compatible storage
- Variant attributes, min order quantity, advanced bulk/wholesale pricing tiers
- Official store flag (`is_official`) with protected admin workflows
- Escrow transaction tracking and scheduled release processing

### Vendor & Admin Operations
- Unified **inventory** panel (admin + vendor) with category tabs (All / Books / Products / Courses / Supermarket)
- **All** tab uses a compact **grid + pagination** layout to avoid endless vertical lists
- Bulk stock actions via shared inventory toolbar
- Vendor order hub with channel filters and editable order/payment status
- Admin dashboard with Plotly analytics API
- Site users, vendors, notifications, escrow admin views

### Messaging & Email
- Unified admin **Messages** center (`/manager/email/`) — inbox, contact messages, compose, reply
- Default sending account synced from `.env` (`admin@duno360.com` via Zoho SMTP)
- Email accounts, auto-rules, labels, and contact message detail/reply flows
- Admin panel i18n dictionary (`admin_i18n.js`) — full EN/FR translation for Messages section

### Localization (i18n)
- Django `LocaleMiddleware` + `locale/en`, `locale/fr` PO catalogs
- `django-modeltranslation` for model fields
- `django-rosetta` for in-browser translation (admin-only)
- Page content catalogs: `manager/page_i18n_catalog.py`, `sync_page_i18n` command (polib compile, no GNU gettext required)
- Client-side admin language toggle (zh / en / fr) with DOM dictionary replacement

### Authentication & Security
- Dual verification at signup: email + SMS OTP (Twilio Verify)
- Session hardening (HttpOnly, SameSite, idle timeout)
- CSRF trusted origins, HTTPS enforcement in production
- Rosetta restricted to admin sessions

### Payments (Africa-focused)
- **KKiaPay** — West Africa mobile money aggregator
- **PawaPay** — Central Africa deposits/payouts/refunds with webhook callbacks
- **MTN MoMo** sandbox/production API
- **Airtel Money** integration
- ngrok helper for local payment callback testing (`run_with_ngrok`)

### AI & Integrations
- AI chatbot widget (OpenRouter) with platform context injection
- Translatebot Django app for translation assistance
- Optional Redis cache for sessions and live presence

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.11+, Django 4.2–5.2 |
| **Database** | PostgreSQL (local dev or Supabase in production) |
| **Cache** | Redis (optional locally; recommended in production) |
| **Media / files** | Pillow, django-storages, boto3 → Supabase Storage (S3-compatible) |
| **Static files** | WhiteNoise + Gunicorn in production |
| **Frontend** | Bootstrap 5, Font Awesome 6, Vanilla JS, Plotly charts |
| **i18n** | django-modeltranslation, django-rosetta, polib, custom page catalogs |
| **Email** | Zoho Mail SMTP (SSL, port 465) |
| **SMS** | Twilio Verify |
| **Payments** | kkiapay SDK, custom PawaPay / MTN MoMo / Airtel Money clients |
| **Dev tooling** | django-extensions, python-dotenv, ngrok (callbacks) |
| **Deployment** | Gunicorn, Nginx, IONOS VPS (Ubuntu 24.04); optional cPanel assets |

---

## Required Environment

### System requirements
- **Python** 3.11 or newer
- **PostgreSQL** 14+ (or Supabase Postgres URL for production)
- **Redis** 6+ (optional for local dev; used for cache/live viewers when `REDIS_URL` is set)
- **Git**

### Minimum `.env` for local development

Copy the template and fill in values:

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Linux / macOS
```

| Variable | Required | Purpose |
|----------|----------|---------|
| `SECRET_KEY` | **Yes** | Django secret key |
| `DEBUG` | **Yes** | `True` locally, `False` in production |
| `ALLOWED_HOSTS` | **Yes** | Comma-separated hostnames |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | **Yes** (local) | PostgreSQL connection |
| `DATABASE_URL` | **Yes** (prod) | Supabase/Postgres URL with `sslmode=require` |
| `CSRF_TRUSTED_ORIGINS` | **Yes** (HTTPS) | Origins allowed for CSRF |

### Email & contact (recommended)

| Variable | Purpose |
|----------|---------|
| `EMAIL_HOST` | SMTP host (default: `smtp.zoho.com`) |
| `EMAIL_PORT` | SMTP port (default: `465`) |
| `EMAIL_USE_SSL` | `True` for Zoho SSL |
| `EMAIL_HOST_USER` | e.g. `admin@duno360.com` |
| `EMAIL_HOST_PASSWORD` | Zoho app password |
| `CONTACT_EMAIL` | Inbound contact address |
| `DEFAULT_FROM_EMAIL` | Outbound From header |
| `PLATFORM_PHONE` | Platform phone/WhatsApp (default: `+242066790386`) |

### Media storage (production)

| Variable | Purpose |
|----------|---------|
| `SUPABASE_STORAGE_ENABLED` | Enable S3-compatible storage |
| `SUPABASE_STORAGE_BUCKET` | Bucket name |
| `SUPABASE_S3_ACCESS_KEY_ID` | S3 access key |
| `SUPABASE_S3_SECRET_ACCESS_KEY` | S3 secret |
| `SUPABASE_S3_ENDPOINT` | S3 endpoint URL |
| `SUPABASE_STORAGE_PUBLIC_BASE_URL` | Public CDN/base URL for media |

### Payments (enable as needed)

| Variable | Service |
|----------|---------|
| `KKIAPAY_*` | KKiaPay keys, sandbox flag, webhook secret |
| `PAWAPAY_*` | PawaPay token, callbacks, currency |
| `MTN_MOMO_*` | MTN MoMo sandbox/production |
| `AIRTEL_MONEY_*` | Airtel Money OAuth + callbacks |

### Signup SMS (optional)

| Variable | Purpose |
|----------|---------|
| `TWILIO_ACCOUNT_SID` | Twilio account |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_VERIFY_SERVICE_SID` | Verify service SID (`VA...`) |

### Cache & dev helpers

| Variable | Purpose |
|----------|---------|
| `REDIS_URL` | e.g. `redis://127.0.0.1:6379/1` |
| `NGROK_ENABLED`, `NGROK_AUTH_TOKEN`, `NGROK_PUBLIC_URL` | Local payment webhooks (dev only) |
| `OPENROUTER_API_KEY` | AI chatbot provider |

### Social media (optional overrides)

| Variable | Default network |
|----------|-----------------|
| `SOCIAL_FACEBOOK_URL` | DUNO 360 Facebook |
| `SOCIAL_INSTAGRAM_URL` | @duno_360 |
| `SOCIAL_TIKTOK_URL` | @duno.360 |
| `SOCIAL_YOUTUBE_URL` | @DUNO360 |

See `.env.example` and `deploy/production.env.example` for the full list with placeholders.

> **Security:** Never commit `.env` or real credentials. Rotate any key that was ever exposed in git history.

---

## Quick Start

```bash
# 1) Clone and enter project
cd book_Project

# 2) Create virtualenv (Windows)
python -m venv .venv
.venv\Scripts\activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Configure environment
copy .env.example .env
# Edit .env — at minimum SECRET_KEY, DEBUG, and database settings

# 5) Create PostgreSQL database, then migrate
python manage.py migrate

# 6) Seed useful defaults (optional)
python manage.py seed_book_categories
python manage.py seed_email_account      # sync admin@duno360.com from .env
python manage.py ensure_official_store   # official DUNO 360 vendor

# 7) Create admin user (Django superuser or manager login as configured)
python manage.py createsuperuser

# 8) Run development server
python manage.py runserver
```

Open:
- Public site: `http://127.0.0.1:8000/manager/public/`
- Admin login: `http://127.0.0.1:8000/manager/login/`
- Messages: `http://127.0.0.1:8000/manager/email/`

### Payment callbacks in local dev

```bash
python manage.py run_with_ngrok
```

Set `NGROK_ENABLED=True` and register callback URLs in KKiaPay / PawaPay dashboards.

---

## Useful Management Commands

```bash
# Database & content
python manage.py migrate
python manage.py seed_book_categories
python manage.py seed_marketplace_demo
python manage.py ensure_official_store

# Email
python manage.py seed_email_account

# i18n
python manage.py sync_page_i18n
python manage.py compilemessages_po

# Payments setup
python manage.py setup_mtn_sandbox
python manage.py seed_kkiapay_countries
python manage.py setup_twilio_verify --create

# Escrow
python manage.py process_escrow_releases

# Utilities
python manage.py check
python manage.py runserver
python manage.py run_with_ngrok
```

---

## Project Structure

```
book_Project/
├── book_Project/          # Django settings, URLs, WSGI
├── manager/               # Bookstore, vendor center, admin, payments, messaging
├── marketplace/           # Products, courses, supermarket, pricing rules
├── locale/                # en/fr translation files
├── deploy/                # IONOS bootstrap scripts, production env template
├── manager/static/        # admin_i18n.js, inventory_grid.js/css, assets
├── manager/templates/     # public, admin, vendor templates
└── requirements.txt
```

**Good entry points for new developers:**
- `manager/views.py` — public flows, admin, vendor, payments
- `marketplace/views.py` — marketplace catalog and vendor forms
- `manager/templates/public/` — storefront UI
- `manager/templates/admin/` — admin panel
- `marketplace/pricing_rules.py` — wholesale pricing logic

---

## Deployment

See **[deploy/README.md](deploy/README.md)** for full IONOS instructions.

### IONOS VPS + Supabase (production)

| | |
|---|---|
| Provider | IONOS |
| IP | `217.160.36.235` |
| OS | Ubuntu 24.04 LTS |
| SSH | `root@217.160.36.235` |

1. Point `duno360.com` A-record to **217.160.36.235** (remove old DigitalOcean IP).
2. SSH into the server and clone the repo to `/opt/duno360/app`.
3. Copy `deploy/production.env.example` → `/opt/duno360/.env` and fill secrets.
4. Run `sudo bash deploy/setup_ionos.sh`.
5. Enable HTTPS: `certbot --nginx -d duno360.com -d www.duno360.com`
6. Restart: `systemctl restart duno360 nginx`

Automated deploy from your PC (SSH key recommended):

```bash
python deploy/deploy_ionos.py
```

### Migrate off DigitalOcean

- Update DNS to the IONOS IP above.
- Decommission the old DigitalOcean droplet when verified.
- Remove `142.93.45.77` from any firewall or `ALLOWED_HOSTS` entries.

### Supabase notes
- Use `DATABASE_URL` with `sslmode=require`.
- URL-encode passwords containing special characters.
- Store media via Supabase Storage S3 credentials — never expose service-role keys in frontend code.

### cPanel
- `passenger_wsgi.py` and `.cpanel.yml` are included for shared-hosting deployments.

---

## Maintenance Checklist

- [ ] Run `migrate` after every pull with schema changes
- [ ] Run `sync_page_i18n` / `compilemessages_po` after content or catalog updates
- [ ] Run `seed_email_account` after changing Zoho credentials
- [ ] Verify vendor inventory and admin inventory grids after stock model changes
- [ ] Test checkout + one payment provider after payment config changes
- [ ] Confirm `DEBUG=False`, HTTPS, and rotated secrets before production releases

---

## License & Support

Proprietary — DUNO 360 platform.  
Support: [admin@duno360.com](mailto:admin@duno360.com) · WhatsApp/call **+242 06 679 03 86**
