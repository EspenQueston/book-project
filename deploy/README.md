# DUNO 360 — Production deployment (IONOS)

Production runs on an **IONOS VPS** (Ubuntu 24.04). DigitalOcean deployment assets have been removed from this repository.

## Server

| Field | Value |
|-------|--------|
| Provider | IONOS |
| Public IP | `217.160.36.235` |
| SSH user | `root` |
| OS | Ubuntu 24.04 LTS |
| App path | `/opt/duno360/app` |
| Env file | `/opt/duno360/.env` |
| systemd | `duno360.service` |
| Domain | `duno360.com` |

> **Security:** Do not store the root password in git. Change the initial IONOS password on first login and prefer SSH keys (`ssh-copy-id root@217.160.36.235`).

## Migrate from DigitalOcean

1. **DNS** — Update the `duno360.com` / `www` A-records to `217.160.36.235`.
2. **Deploy** on the IONOS server (steps below).
3. **Decommission** the old DigitalOcean droplet from the DigitalOcean control panel when the new site is verified.
4. Remove `142.93.45.77` from any `ALLOWED_HOSTS` / firewall rules.

## First-time setup (IONOS console or SSH)

```bash
# As root on 217.160.36.235
git clone https://github.com/EspenQueston/book-project.git /opt/duno360/app
cp /opt/duno360/app/deploy/production.env.example /opt/duno360/.env
nano /opt/duno360/.env   # fill DATABASE_URL, SECRET_KEY, email, payments, etc.
bash /opt/duno360/app/deploy/setup_ionos.sh
```

Or paste the full bootstrap script from `deploy/ionos_console_bootstrap.sh` into the IONOS KVM console.

## HTTPS

After HTTP works:

```bash
certbot --nginx -d duno360.com -d www.duno360.com
```

Set `FORCE_HTTPS=True` in `/opt/duno360/.env` and restart:

```bash
systemctl restart duno360
```

## Deploy updates

From your local machine (SSH key auth recommended):

```bash
# Set secrets locally — see deploy/.env.local.example
python deploy/deploy_ionos.py
```

Or paste this on the server (root shell — FinalShell, IONOS KVM console, or SSH):

```bash
set -e
chown -R duno360:www-data /opt/duno360/app || true
if ! command -v msgfmt >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq && apt-get install -y gettext
fi
sudo -u duno360 bash -lc 'cd /opt/duno360/app && git -c safe.directory=/opt/duno360/app fetch origin && git -c safe.directory=/opt/duno360/app checkout -- locale/en/LC_MESSAGES/django.mo locale/fr/LC_MESSAGES/django.mo 2>/dev/null || true && git -c safe.directory=/opt/duno360/app reset --hard HEAD && git -c safe.directory=/opt/duno360/app pull origin main'
sudo -u duno360 bash -lc 'cd /opt/duno360/app && set -a && . /opt/duno360/.env && set +a && .venv/bin/python manage.py migrate --noinput && .venv/bin/python manage.py collectstatic --noinput && .venv/bin/python manage.py compilemessages -l en -l fr'
systemctl restart duno360
systemctl is-active duno360
```

This covers the whole app in one pass — books, marketplace (products/courses/supermarket), templates, static files, and translations — since it's all one Django codebase in a single git pull. The `checkout -- *.mo` step discards any stale compiled translation binaries before pulling so `git pull` never conflicts with locally-compiled `.mo` files.

Quick remote update (password via env var, not in repo):

```bash
set DUNO360_ROOT_PASS=your-root-password
set DUNO360_VPS_HOST=217.160.36.235
python deploy/remote_prod_update.py
```

## Syncing local database content to production (without overwriting it)

Code changes go through git (above). **Data** you created locally — new
books, marketplace products/courses/supermarket items, categories — is a
separate concern: it lives in your local Postgres, not in git, and
production has its own live data (real orders, users, vendors, inventory
counts) that must never be clobbered by a local snapshot.

`deploy/sync_content_to_production.py` does this safely:

- Matches rows by **natural key** (slug / title / name) — never by raw
  primary key, since local and production auto-increment IDs don't
  correspond to the same real-world rows.
- **Upserts only** — creates new rows and updates existing catalog rows it
  recognizes; it never deletes anything in production.
- Covers the whole catalog: `Publisher`, `BookCategory`, `Book`, `Author`
  (books) and `Category`, `Product`, `Course` + sections/lessons,
  `SupermarketItem` (marketplace) — but deliberately **excludes** users,
  vendors, orders, wallets, and messages, so it can never touch live
  transactional data or overwrite production's real inventory counts.
- Defaults to **dry-run** (prints a report, writes nothing) until you pass
  `--apply`, and takes a JSON backup of every production row it's about to
  touch before writing anything.

```powershell
# 1) Set the production connection string (Supabase dashboard → Settings → Database):
$env:PRODUCTION_DATABASE_URL = 'postgresql://...'

# 2) Dry run first — review the report, nothing is written:
python deploy/sync_content_to_production.py

# 3) Once the report looks right, actually write:
python deploy/sync_content_to_production.py --apply
```

Run this **before** deploying code that depends on the new content (e.g. a
template referencing a new category) — it only touches the database, not
static files, so it's independent of the git-pull deploy step above.

## Files in this folder

| File | Purpose |
|------|---------|
| `setup_ionos.sh` | Main server bootstrap (nginx, gunicorn, systemd) |
| `ionos_console_bootstrap.sh` | One-shot paste script for IONOS console |
| `deploy_ionos.py` | Automated first deploy from local machine via SSH |
| `remote_prod_update.py` | Pull + migrate + restart on production |
| `sync_content_to_production.py` | Safe upsert of local catalog content (books + marketplace) into production |
| `production.env.example` | Template for `/opt/duno360/.env` |
| `.env.local.example` | Local secrets for `deploy_ionos.py` (gitignored) |
