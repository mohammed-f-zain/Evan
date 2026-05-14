#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -f .env ]]; then
  echo "Missing .env" >&2
  exit 1
fi
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-evanodoo}"
docker compose run --rm odoo odoo \
  -d Evan \
  -i base,base_accounting_kit \
  --stop-after-init \
  --without-demo=all
echo "Database Evan initialized with base_accounting_kit (dependencies auto-installed)."
