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

Or on the server:

```bash
cd /opt/duno360/app
sudo -u duno360 git pull origin main
set -a && source /opt/duno360/.env && set +a
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
systemctl restart duno360
```

Quick remote update (password via env var, not in repo):

```bash
set DUNO360_ROOT_PASS=your-root-password
set DUNO360_VPS_HOST=217.160.36.235
python deploy/remote_prod_update.py
```

## Files in this folder

| File | Purpose |
|------|---------|
| `setup_ionos.sh` | Main server bootstrap (nginx, gunicorn, systemd) |
| `ionos_console_bootstrap.sh` | One-shot paste script for IONOS console |
| `deploy_ionos.py` | Automated first deploy from local machine via SSH |
| `remote_prod_update.py` | Pull + migrate + restart on production |
| `production.env.example` | Template for `/opt/duno360/.env` |
| `.env.local.example` | Local secrets for `deploy_ionos.py` (gitignored) |
