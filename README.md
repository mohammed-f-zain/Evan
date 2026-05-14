# Evan — Odoo 18 Community monorepo

Dockerized **Odoo 18.0** with **PostgreSQL 16**, custom addons under `addons/custom/` (`base_account_budget`, **base_accounting_kit**), and deployment assets for **evanwater.online**.

## Local / server layout

- `docker-compose.yml` — `odoo` (custom image) + `db`
- `Dockerfile` — extends `odoo:18.0`, installs Python deps required by the accounting kit (`openpyxl`, `ofxparse`, `qifparse`)
- `config/odoo.conf.in` — template; rendered to `config/odoo.conf` (gitignored) with secrets from `.env`
- `deploy/` — nginx site + `remote-bootstrap.sh` (run on the server)
- `scripts/push-deploy.sh` — rsync to the server and run bootstrap

## First-time on any machine

1. `cp .env.example .env` and set `POSTGRES_PASSWORD` and `ODOO_ADMIN_PASSWORD`.
2. `bash scripts/render-config.sh`
3. `docker compose build --pull && docker compose up -d`
4. Create/init DB **Evan** (if not already): `bash scripts/init-evan-db.sh`

## Deploy to the VPS

From this directory (SSH key **or** `DEPLOY_SSH_PASSWORD` for password auth):

```bash
./scripts/push-deploy.sh
```

Server install path defaults to `/opt/evan-odoo`. On first bootstrap the server creates `/opt/evan-odoo/.env` and `/root/evan-odoo.credentials` with generated DB and Odoo **master** passwords.

## HTTPS

If Let’s Encrypt fails (DNS/CAA/propagation), the site still serves **HTTP**. After DNS is correct, on the server run:

`certbot --nginx -d evanwater.online -d www.evanwater.online`

## Odoo login

Use database **Evan** on the login screen. Set the internal **admin** password on first login if the instance still uses the default (change it immediately). The value in `.env` named `ODOO_ADMIN_PASSWORD` is the **database manager / master** password from `admin_passwd` in `odoo.conf`, not the web user password.
