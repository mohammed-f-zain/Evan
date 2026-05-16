#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -f .env ]]; then
  echo "Missing .env" >&2
  exit 1
fi
docker compose run --rm odoo odoo \
  -d Evan \
  -i base,base_accounting_kit,custom_account_reports_enterprise \
  --stop-after-init \
  --without-demo=all
echo "Database Evan initialized with base_accounting_kit and custom_account_reports_enterprise."
