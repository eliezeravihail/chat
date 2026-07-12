#!/usr/bin/env bash
# =====================================================================
# ntfy channel for Hermes — filtered-phone friendly (no VPN required).
#
# Default mode (A): public ntfy.sh with LONG RANDOM topic names.
#   - Works through filtered phones that already allow ntfy.sh.
#   - The random topic acts as a 25+ char password (unguessable).
#   - Transport is TLS end to end; trade-off: ntfy.sh servers can see
#     message content (same class of trust as any hosted relay).
#
# Privacy mode (B, later): self-hosted ntfy behind HTTPS on this VM
#   (DuckDNS domain + Caddy). Requires the phone's filter to allow the
#   new domain — coordinate with the filtering provider first. Not
#   automated here; see HERMES.md.
#
# Usage:  bash setup-ntfy-server.sh          (run after setup-hermes-vm.sh)
# Safe to re-run; keeps existing topics unless NTFY_REGEN=1.
# =====================================================================
set -euo pipefail

HH="${HERMES_HOME:-$HOME/.hermes}"
mkdir -p "$HH" && touch "$HH/.env" && chmod 600 "$HH/.env"

rand_topic() {
  # 25 url-safe chars from /dev/urandom — effectively a strong password.
  tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 25
}

get_env() { grep -s "^$1=" "$HH/.env" | head -1 | cut -d= -f2-; }
set_env() {
  grep -q "^$1=" "$HH/.env" 2>/dev/null \
    && sed -i "s|^$1=.*|$1=$2|" "$HH/.env" \
    || echo "$1=$2" >> "$HH/.env"
}

TOPIC_IN="$(get_env NTFY_TOPIC)"
TOPIC_OUT="$(get_env NTFY_PUBLISH_TOPIC)"
if [ -z "$TOPIC_IN" ] || [ "${NTFY_REGEN:-0}" = "1" ]; then
  TOPIC_IN="hm-in-$(rand_topic)"
  TOPIC_OUT="hm-out-$(rand_topic)"
fi

set_env NTFY_SERVER_URL    "https://ntfy.sh"
set_env NTFY_TOPIC         "$TOPIC_IN"
set_env NTFY_PUBLISH_TOPIC "$TOPIC_OUT"
set_env NTFY_ALLOW_ALL_USERS "true"   # topic secrecy is the gate on ntfy.sh

echo "============================================================"
echo "✅ ערוץ ntfy מוגדר (ntfy.sh ציבורי, נושאים אקראיים-סודיים)."
echo
echo "בטלפון, באפליקציית ntfy:"
echo "  1) Subscribe to topic:  ${TOPIC_OUT}"
echo "       (שם מגיעות תשובות הבוט)"
echo "  2) כדי לכתוב לבוט: פתח את הנושא ${TOPIC_IN} ופרסם אליו הודעה,"
echo "     או שמור את שניהם: כתיבה ל-${TOPIC_IN}, קריאה מ-${TOPIC_OUT}."
echo
echo "⚠️ הנושאים האלה הם הסוד — אל תשתף אותם. להחלפה: NTFY_REGEN=1 והרצה שוב."
echo
echo "הפעל מחדש את ה-gateway:  hermes gateway restart   (או run)"
echo "============================================================"
