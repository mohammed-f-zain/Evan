#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
SERVER="${DEPLOY_SERVER:-root@187.127.86.53}"
DEST="${DEPLOY_DEST:-/opt/evan-odoo}"

if [[ -n "${DEPLOY_SSH_PASSWORD:-}" ]]; then
  export SSHPASS="${DEPLOY_SSH_PASSWORD}"
  RSYNC_SSH="sshpass -e ssh -o StrictHostKeyChecking=accept-new"
  REMOTE=(sshpass -e ssh -o StrictHostKeyChecking=accept-new "$SERVER")
else
  RSYNC_SSH="ssh -o StrictHostKeyChecking=accept-new"
  REMOTE=(ssh -o StrictHostKeyChecking=accept-new "$SERVER")
fi

"${REMOTE[@]}" "mkdir -p '$DEST'"
rsync -az -e "$RSYNC_SSH" \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude 'config/odoo.conf' \
  --exclude '__pycache__/' \
  --exclude '*.pyc' \
  "$ROOT/" "$SERVER:$DEST/"

"${REMOTE[@]}" "chmod +x '$DEST/deploy/remote-bootstrap.sh' '$DEST/scripts/'*.sh && APP_DIR='$DEST' bash '$DEST/deploy/remote-bootstrap.sh'"
echo "Deploy finished."
