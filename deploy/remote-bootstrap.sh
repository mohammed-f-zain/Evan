#!/usr/bin/env bash
# Run on the server as root after code is in /opt/evan-odoo
set -euo pipefail
APP_DIR="${APP_DIR:-/opt/evan-odoo}"
cd "$APP_DIR"

export DEBIAN_FRONTEND=noninteractive

install_packages() {
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg lsb-release rsync nginx certbot python3-certbot-nginx python3
}

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  install_packages
  curl -fsSL https://get.docker.com | sh
elif ! command -v certbot >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
  install_packages
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
  POSTGRES_PASSWORD="$(openssl rand -hex 24)"
  ODOO_ADMIN_PASSWORD="$(openssl rand -hex 24)"
  cat >"$APP_DIR/.env" <<EOF
POSTGRES_USER=odoo
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
ODOO_ADMIN_PASSWORD=${ODOO_ADMIN_PASSWORD}
EOF
  umask 077
  {
    echo "Evan Odoo credentials (store in a password manager):"
    echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}"
    echo "ODOO_ADMIN_PASSWORD=${ODOO_ADMIN_PASSWORD}"
  } >/root/evan-odoo.credentials
  echo "Created $APP_DIR/.env and /root/evan-odoo.credentials"
fi

# Production uses default port 8069 on localhost (see docker-compose.yml).
if [[ -f "$APP_DIR/.env" ]]; then
  sed -i '/^ODOO_HTTP_PORT=/d' "$APP_DIR/.env"
fi

set -a
# shellcheck disable=SC1091
source "$APP_DIR/.env"
set +a

bash "$APP_DIR/scripts/render-config.sh"
docker compose build --pull
docker compose up -d

sleep 10
EVAN_EXISTS=0
if docker compose exec -T db psql -U "${POSTGRES_USER:-odoo}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='Evan'" | grep -q 1; then
  EVAN_EXISTS=1
fi

NEEDS_INIT=0
if [[ "$EVAN_EXISTS" -eq 0 ]]; then
  NEEDS_INIT=1
else
  KIT_INSTALLED="$(docker compose exec -T db psql -U "${POSTGRES_USER:-odoo}" -d Evan -tAc "SELECT count(*) FROM ir_module_module WHERE name='base_accounting_kit' AND state='installed'" 2>/dev/null | tr -d '[:space:]' || echo 0)"
  if [[ "${KIT_INSTALLED:-0}" != "1" ]]; then
    docker compose exec -T db psql -U "${POSTGRES_USER:-odoo}" -d postgres -c \
      "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'Evan' AND pid <> pg_backend_pid();" \
      >/dev/null 2>&1 || true
    docker compose exec -T db psql -U "${POSTGRES_USER:-odoo}" -d postgres -c 'DROP DATABASE IF EXISTS "Evan";'
    NEEDS_INIT=1
  fi
fi

if [[ "$NEEDS_INIT" -eq 1 ]]; then
  docker compose run --rm odoo odoo \
    -d Evan \
    -i base,base_accounting_kit,custom_account_reports_enterprise \
    --stop-after-init \
    --without-demo=all
fi

docker compose up -d

REPORTS_INSTALLED=0
if docker compose exec -T db psql -U "${POSTGRES_USER:-odoo}" -d Evan -tAc \
  "SELECT 1 FROM ir_module_module WHERE name='custom_account_reports_enterprise' AND state='installed'" \
  | grep -q 1; then
  REPORTS_INSTALLED=1
fi
if [[ "$REPORTS_INSTALLED" -eq 0 && "$EVAN_EXISTS" -eq 1 ]]; then
  docker compose run --rm odoo odoo \
    -d Evan \
    -i custom_account_reports_enterprise \
    --stop-after-init
  docker compose up -d
fi

install -m 644 "$APP_DIR/deploy/nginx/odoo-evanwater.conf" /etc/nginx/sites-available/odoo-evanwater.conf
ln -sf /etc/nginx/sites-available/odoo-evanwater.conf /etc/nginx/sites-enabled/odoo-evanwater.conf
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

if certbot certificates 2>/dev/null | grep -q "evanwater.online"; then
  certbot install --cert-name evanwater.online --nginx --redirect --non-interactive || true
fi

if ! certbot certificates 2>/dev/null | grep -q "evanwater.online"; then
  if ! certbot --nginx -d evanwater.online -d www.evanwater.online --non-interactive --agree-tos --email "admin@evanwater.online" --redirect; then
    echo "Certbot failed (often DNS/CAA or propagation). HTTP still works; fix DNS then run on server:" >&2
    echo "  certbot --nginx -d evanwater.online -d www.evanwater.online" >&2
  fi
else
  certbot renew --nginx --quiet || true
fi

echo "Bootstrap complete. Open https://evanwater.online and select database Evan."
