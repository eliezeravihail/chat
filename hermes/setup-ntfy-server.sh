#!/usr/bin/env bash
# =====================================================================
# SELF-HOSTED ntfy server for Hermes, on the same free VM, with public
# HTTPS — so the phone's existing ntfy app just points at OUR server.
# No VPN, no app installs; works on a phone that can't install apps as
# long as its network is open.
#
#   phone (ntfy app) --HTTPS--> Caddy --> ntfy (localhost) <--> Hermes
#
# Auth is username+password (server denies everything else), so topic
# names can be SIMPLE and memorable (default: chat / bot) — no random
# secrets to remember.
#
# One-time prerequisites (5 minutes, on any computer):
#   1. Free subdomain at https://www.duckdns.org (login, add a domain,
#      copy the token). Example below uses mybot.duckdns.org.
#   2. In GCP Console → the VM → Edit → check "Allow HTTP traffic" AND
#      "Allow HTTPS traffic" → Save. (Needed for the certificate + app.)
#
# Usage:
#   DUCKDNS_SUBDOMAIN=mybot DUCKDNS_TOKEN=xxxx \
#   NTFY_USER=eliezer NTFY_PASSWORD=strong-pass bash setup-ntfy-server.sh
# Or run bare and answer prompts. Safe to re-run.
# =====================================================================
set -euo pipefail

if [ -z "${DUCKDNS_SUBDOMAIN:-}" ]; then read -rp  "DuckDNS subdomain (the part before .duckdns.org): " DUCKDNS_SUBDOMAIN; fi
if [ -z "${DUCKDNS_TOKEN:-}" ];     then read -rp  "DuckDNS token: " DUCKDNS_TOKEN; fi
if [ -z "${NTFY_USER:-}" ];         then read -rp  "ntfy username: " NTFY_USER; fi
if [ -z "${NTFY_PASSWORD:-}" ];     then read -rsp "ntfy password: " NTFY_PASSWORD; echo; fi
TOPIC_IN="${NTFY_TOPIC:-chat}"        # you publish here (questions)
TOPIC_OUT="${NTFY_PUBLISH_TOPIC:-bot}" # bot replies here (subscribe)
DOMAIN="${DUCKDNS_SUBDOMAIN}.duckdns.org"
NTFY_PORT=2586

echo "==> 1/6 point ${DOMAIN} at this VM (and keep it updated)"
curl -fsS "https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&ip=" >/dev/null && echo "    DuckDNS updated"
( crontab -l 2>/dev/null | grep -v duckdns.org ; \
  echo "*/5 * * * * curl -fsS \"https://www.duckdns.org/update?domains=${DUCKDNS_SUBDOMAIN}&token=${DUCKDNS_TOKEN}&ip=\" >/dev/null 2>&1" ) | crontab -

echo "==> 2/6 install ntfy server"
if ! command -v ntfy >/dev/null; then
  sudo mkdir -p /etc/apt/keyrings
  curl -fsSL https://archive.heckel.io/apt/pubkey.txt | sudo gpg --dearmor -o /etc/apt/keyrings/archive.heckel.io.gpg
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/archive.heckel.io.gpg] https://archive.heckel.io/apt debian main" \
    | sudo tee /etc/apt/sources.list.d/archive.heckel.io.list >/dev/null
  sudo apt-get update -qq && sudo apt-get install -y -qq ntfy
fi

echo "==> 3/6 configure ntfy (auth: deny-all + your user only)"
sudo mkdir -p /var/lib/ntfy /etc/ntfy
sudo tee /etc/ntfy/server.yml >/dev/null <<EOF
base-url: https://${DOMAIN}
listen-http: "127.0.0.1:${NTFY_PORT}"
behind-proxy: true
auth-file: /var/lib/ntfy/auth.db
auth-default-access: deny-all
cache-file: /var/lib/ntfy/cache.db
EOF
sudo systemctl enable --now ntfy && sleep 1
sudo NTFY_PASSWORD="${NTFY_PASSWORD}" ntfy user add --role=user "${NTFY_USER}" 2>/dev/null || true
sudo ntfy access "${NTFY_USER}" "${TOPIC_IN}"  rw
sudo ntfy access "${NTFY_USER}" "${TOPIC_OUT}" rw

echo "==> 4/6 install Caddy (automatic HTTPS certificate)"
if ! command -v caddy >/dev/null; then
  sudo apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https >/dev/null
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -qq && sudo apt-get install -y -qq caddy
fi
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
${DOMAIN} {
    reverse_proxy 127.0.0.1:${NTFY_PORT}
}
EOF
sudo systemctl reload caddy || sudo systemctl restart caddy

echo "==> 5/6 wire Hermes to the local ntfy"
HH="${HERMES_HOME:-$HOME/.hermes}"
mkdir -p "$HH" && touch "$HH/.env" && chmod 600 "$HH/.env"
set_env() {
  grep -q "^$1=" "$HH/.env" 2>/dev/null \
    && sed -i "s|^$1=.*|$1=$2|" "$HH/.env" \
    || echo "$1=$2" >> "$HH/.env"
}
set_env NTFY_SERVER_URL     "http://127.0.0.1:${NTFY_PORT}"
set_env NTFY_TOPIC          "${TOPIC_IN}"
set_env NTFY_PUBLISH_TOPIC  "${TOPIC_OUT}"
set_env NTFY_TOKEN          "${NTFY_USER}:${NTFY_PASSWORD}"
set_env NTFY_ALLOW_ALL_USERS "true"   # server auth is the real gate

echo "==> 6/6 done"
echo "============================================================"
echo "✅ שרת ntfy פרטי רץ ב-https://${DOMAIN}"
echo
echo "בטלפון, באפליקציית ntfy (שכבר מותקנת):"
echo "  1) Settings → Manage users → Add:"
echo "       Server: https://${DOMAIN}"
echo "       User:   ${NTFY_USER}   +  הסיסמה"
echo "  2) + → Subscribe to topic → ${TOPIC_OUT}"
echo "       (סמן Use another server והזן https://${DOMAIN})"
echo "       ← כאן מגיעות תשובות הבוט"
echo "  3) לשאול את הבוט: הירשם גם ל-${TOPIC_IN} ופרסם אליו הודעות"
echo "       (חץ השליחה בתוך הנושא)"
echo
echo "והפעל מחדש את ה-gateway:  hermes gateway restart  (או run)"
echo
echo "⚠️ ודא שב-GCP סימנת Allow HTTP + Allow HTTPS על ה-VM, אחרת"
echo "   התעודה לא תונפק. בדיקה: פתח https://${DOMAIN} בדפדפן — אמור"
echo "   להופיע דף ntfy."
echo "============================================================"
