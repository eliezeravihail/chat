#!/usr/bin/env bash
# =====================================================================
# One-shot deploy of the Twilio polling bot on a fresh Ubuntu VM
# (e.g. Google Cloud e2-micro, always-free). Sets up Python, clones the
# repo, writes .env, and runs twilio_poll.py under a systemd service so
# it survives SSH disconnects and reboots — no tmux babysitting.
#
# Usage (fill in your values):
#   OPENROUTER_KEY=sk-or-... \
#   TWILIO_ACCOUNT_SID=AC... TWILIO_AUTH_TOKEN=... \
#   TWILIO_FROM=whatsapp:+14155238886 \
#   ALLOWED_WA_ID=whatsapp:+9725XXXXXXXX,whatsapp:+9725YYYYYYYY \
#     bash setup-twilio-vm.sh
#
# Or run bare and answer the prompts. Safe to re-run (updates + restarts).
# =====================================================================
set -euo pipefail

REPO="https://github.com/eliezeravihail/chat.git"
DIR="$HOME/chat"

ask() { local v; if [ -z "${!1:-}" ]; then read -rp "$2: " v; printf -v "$1" '%s' "$v"; fi; }
ask OPENROUTER_KEY     "OpenRouter API key (sk-or-...)"
ask TWILIO_ACCOUNT_SID "Twilio Account SID (AC...)"
ask TWILIO_AUTH_TOKEN  "Twilio Auth Token"
TWILIO_FROM="${TWILIO_FROM:-whatsapp:+14155238886}"
ask ALLOWED_WA_ID      "Allowed WhatsApp numbers, comma-separated (e.g. whatsapp:+9725...)"

echo "==> 1/4 system packages"
sudo apt-get update -qq
sudo apt-get install -y -qq git python3 python3-venv python3-pip >/dev/null

echo "==> 2/4 code + dependencies"
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull --ff-only; else git clone -q "$REPO" "$DIR"; fi
cd "$DIR"
python3 -m venv .venv
./.venv/bin/pip install -q --upgrade pip
./.venv/bin/pip install -q -r requirements.txt

echo "==> 3/4 .env"
cat > "$DIR/.env" <<EOF
OPENROUTER_KEY=${OPENROUTER_KEY}
TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
TWILIO_FROM=${TWILIO_FROM}
ALLOWED_WA_ID=${ALLOWED_WA_ID}
EOF
chmod 600 "$DIR/.env"

echo "==> 4/4 systemd service (auto-start, auto-restart)"
sudo tee /etc/systemd/system/wa-bot.service >/dev/null <<EOF
[Unit]
Description=Twilio WhatsApp polling bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=${DIR}
ExecStart=${DIR}/.venv/bin/python ${DIR}/twilio_poll.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now wa-bot.service
sleep 2

echo "============================================================"
echo "✅ הבוט רץ כשירות. פקודות שימושיות:"
echo "   sudo systemctl status wa-bot     ← מצב"
echo "   journalctl -u wa-bot -f          ← לוגים חיים"
echo "   sudo systemctl restart wa-bot    ← הפעלה מחדש"
echo
echo "לעדכון קוד בעתיד:  cd ~/chat && git pull && sudo systemctl restart wa-bot"
echo
echo "⚠️ עדיין sandbox → מגבלת 50 הודעות/יום. שלח הודעה מהמספר המורשה לבדיקה."
echo "============================================================"
