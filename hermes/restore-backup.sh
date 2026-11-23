#!/usr/bin/env bash
# =====================================================================
# Restore an encrypted snapshot made by .github/workflows/backup-memory.yml
# onto a VM that already ran setup-hermes-vm.sh with the SAME
# HERMES_MEMORY_KEY (the snapshot is encrypted with that key).
#
# Usage (on the VM):
#   1. download the newest snapshots/hermes-*.tar.enc from the private backups
#      repo to the VM (e.g. with `git clone` of that repo, or scp from your phone's
#      file manager over the SSH console), then:
#   2. bash ~/chat/hermes/restore-backup.sh /path/to/hermes-YYYYMMDD-HHMM.tar.enc
#      add --with-whatsapp to ALSO restore the WhatsApp link (only if the OLD VM
#      is gone for good — two machines on one link = immediate logout).
#
# The gateway is stopped during the restore and started afterwards. The
# current state.db is kept as state.db.prerestore.<timestamp>.
# =====================================================================
set -euo pipefail
export PATH="$HOME/.local/bin:$HOME/bin:$HOME/hermes-env/bin:$PATH"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"

SNAP="${1:-}"; WITH_WA=0
[ "${2:-}" = "--with-whatsapp" ] && WITH_WA=1
[ -f "$SNAP" ] || { echo "usage: restore-backup.sh <hermes-*.tar.enc> [--with-whatsapp]" >&2; exit 1; }
[ -f "$HOME/.hermes.key" ] || { echo "no ~/.hermes.key — run setup-hermes-vm.sh first (with HERMES_MEMORY_KEY)" >&2; exit 1; }

HH="${HERMES_HOME:-$HOME/.hermes}"
sudo systemctl start hermes-crypt >/dev/null 2>&1 || true
mountpoint -q "$HH" || gocryptfs -allow_other -passfile "$HOME/.hermes.key" "$HOME/.hermes.cipher" "$HH"

T="$HH/.restore-stage"; rm -rf "$T"; mkdir -p "$T"; trap 'rm -rf "$T"' EXIT
echo "==> decrypting (wrong key = 'bad decrypt')"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$HOME/.hermes.key" -in "$SNAP" | tar -C "$T" -xzf -
echo "    snapshot taken at: $(cat "$T/BACKUP_TIME" 2>/dev/null || echo unknown)"

echo "==> stopping the gateway"
systemctl --user stop hermes-gateway 2>/dev/null || true
fuser -k 3000/tcp 2>/dev/null || true
sleep 2

STAMP="$(date +%Y%m%d%H%M%S)"
if [ -f "$T/state.db" ]; then
  [ -f "$HH/state.db" ] && mv "$HH/state.db" "$HH/state.db.prerestore.$STAMP"
  rm -f "$HH/state.db-wal" "$HH/state.db-shm"
  cp "$T/state.db" "$HH/state.db"
  echo "==> state.db restored ($(stat -c%s "$HH/state.db") bytes; previous kept as state.db.prerestore.$STAMP)"
fi
if [ -d "$T/memories" ]; then
  mkdir -p "$HH/memories" && cp -r "$T/memories/." "$HH/memories/"
fi
if [ "$WITH_WA" = "1" ] && [ -d "$T/whatsapp/session" ]; then
  rm -rf "$HH/whatsapp/session" "$HH/platforms/whatsapp/session"
  mkdir -p "$HH/whatsapp" && cp -r "$T/whatsapp/session" "$HH/whatsapp/"
  echo "==> WhatsApp link restored (no QR needed if the old VM is offline)"
else
  echo "    (WhatsApp link not restored — pair with: bash ~/chat/hermes/repair-whatsapp.sh)"
fi

echo "==> starting the gateway"
sudo loginctl enable-linger "$(whoami)" 2>/dev/null || true
systemctl --user start hermes-gateway 2>/dev/null || echo "start the gateway: bash ~/chat/hermes/repair-whatsapp.sh --keep"
echo "done."
