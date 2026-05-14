#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if [[ ! -f .env ]]; then
  echo "Missing .env. Copy .env.example to .env and set passwords." >&2
  exit 1
fi
set -a
# shellcheck disable=SC1091
source .env
set +a
export ROOT ODOO_ADMIN_PASSWORD POSTGRES_USER POSTGRES_PASSWORD
python3 - <<'PY'
import os
from pathlib import Path
root = Path(os.environ["ROOT"])
text = (root / "config" / "odoo.conf.in").read_text()
repl = {
    "__ODOO_ADMIN_PASSWORD__": os.environ["ODOO_ADMIN_PASSWORD"],
    "__POSTGRES_USER__": os.environ["POSTGRES_USER"],
    "__POSTGRES_PASSWORD__": os.environ["POSTGRES_PASSWORD"],
}
for k, v in repl.items():
    text = text.replace(k, v)
out = root / "config" / "odoo.conf"
out.write_text(text)
out.chmod(0o644)
print(f"Wrote {out}")
PY
