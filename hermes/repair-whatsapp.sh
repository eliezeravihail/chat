#!/usr/bin/env bash
# =====================================================================
# Clean WhatsApp (re)pair for the Hermes bot — ONE command instead of a
# dozen manual steps, in the order that actually works.
#
# Why this exists: WhatsApp drops a linked device ("Logged out", 401
# conflict / device_removed) when two processes use the same session at
# once, or when the pairing is interrupted (Ctrl+C / restart) before the
# first minutes of registration finish. Every failed re-pair in Aug 2026
# had one of those two causes. This script enforces the safe sequence:
#
#   1. stop the gateway service + kill every stray gateway/bridge process
#   2. (default) wipe the old session in BOTH locations Hermes may read
#   3. run `hermes whatsapp` interactively — scan the FIRST QR immediately
#   4. start the gateway service right away, then HANDS OFF for 5 minutes
#
# Usage (over SSH on the VM):
#   bash ~/chat/hermes/repair-whatsapp.sh            # full re-pair (QR scan)
#   bash ~/chat/hermes/repair-whatsapp.sh --keep     # keep creds, just clean-restart
#
# Conversation memory (state.db) is NOT touched — the WhatsApp link and the
# chat history are separate stores.
# =====================================================================
set -u
export PATH="$HOME/.local/bin:$HOME/bin:$HOME/hermes-env/bin:$PATH"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"

KEEP=0
[ "${1:-}" = "--keep" ] && KEEP=1

HH="${HERMES_HOME:-$HOME/.hermes}"
S1="$HH/whatsapp/session"
S2="$HH/platforms/whatsapp/session"

if ! command -v hermes >/dev/null 2>&1; then
  echo "hermes not on PATH — run from the VM where Hermes is installed." >&2
  exit 1
fi
if ! mountpoint -q "$HH" 2>/dev/null && [ -d "$HOME/.hermes.cipher" ]; then
  echo "==> mounting encrypted store"
  sudo systemctl start hermes-crypt 2>/dev/null \
    || gocryptfs -allow_other -passfile "$HOME/.hermes.key" "$HOME/.hermes.cipher" "$HH" || true
fi

echo "==> 1/4 stopping every gateway / bridge process"
systemctl --user stop hermes-gateway 2>/dev/null || true
sudo systemctl stop hermes-gateway 2>/dev/null || true
hermes gateway stop >/dev/null 2>&1 || true
tmux kill-server 2>/dev/null || true
# Kill by PORT first (the bridge is an HTTP server on 3000), then by name.
fuser -k 3000/tcp 2>/dev/null || true
pkill -9 -f 'hermes gateway' 2>/dev/null || true
pkill -9 -f 'whatsapp-bridge/bridge.js' 2>/dev/null || true
sleep 3
LEFT="$(pgrep -af 'hermes gateway|whatsapp-bridge/bridge.js' 2>/dev/null || true)"
if [ -n "$LEFT" ]; then
  echo "still running — aborting so we don't pair with two processes alive:" >&2
  echo "$LEFT" | sed -E 's/[0-9]{6,}/<num>/g' >&2
  exit 1
fi
echo "    clean."

if [ "$KEEP" = "1" ]; then
  echo "==> 2/4 keeping existing session (--keep)"
  if [ ! -f "$S1/creds.json" ] && [ ! -f "$S2/creds.json" ]; then
    echo "    no creds.json found — run without --keep to pair." >&2
    exit 1
  fi
else
  echo "==> 2/4 wiping old WhatsApp session (both locations; memory untouched)"
  rm -rf "$S1" "$S2"
  mkdir -p "$S1"
  echo "==> 3/4 pairing. Answer the prompts: 'Update allowed users?' → N,"
  echo "    'Re-pair?' (if asked) → y. When the QR appears, scan the FIRST one at once:"
  echo "    phone → WhatsApp → Linked devices → Link a device."
  echo "    Do NOT press Ctrl+C. Wait for 'Pairing complete'."
  echo
  # Interactive on purpose (no piped stdin): the wizard uses input() and an
  # unexpected prompt on a closed stdin would crash it mid-pairing.
  hermes whatsapp || {
    echo "pairing did not complete — nothing started. Run again when ready." >&2
    exit 1
  }
  if [ ! -f "$S1/creds.json" ]; then
    echo "no creds.json after pairing — not starting the gateway." >&2
    exit 1
  fi
fi

echo "==> 4/4 starting the gateway service (single process, right away)"
sudo loginctl enable-linger "$(whoami)" 2>/dev/null || true
if ! systemctl --user cat hermes-gateway >/dev/null 2>&1; then
  hermes gateway install >/dev/null 2>&1 || true
fi
systemctl --user start hermes-gateway 2>/dev/null \
  || sudo systemctl start hermes-gateway 2>/dev/null \
  || { echo "no systemd unit — install one with: hermes gateway install" >&2; exit 1; }

echo
echo "Started. NOW: do nothing for 5 minutes — no restart, no Ctrl+C, no"
echo "'hermes gateway', no copying files. WhatsApp finishes registering the"
echo "device in the first minutes; interrupting that is what broke it before."
echo
echo "After 5 min, check:"
echo "  systemctl --user is-active hermes-gateway"
echo "  tail -5 $HH/whatsapp/bridge.log      # want: 'WhatsApp connected!'"
echo "and the device should be listed under Linked devices on the phone."
