#!/usr/bin/env bash
# Install or upgrade custom modules on an existing Evan database.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -f .env ]]; then
  echo "Missing .env — copy .env.example to .env first." >&2
  exit 1
fi
MODULES="${1:-custom_account_reports_enterprise}"
docker compose run --rm odoo odoo \
  -d Evan \
  -u "${MODULES}" \
  --stop-after-init
echo "Upgraded module(s): ${MODULES}"
