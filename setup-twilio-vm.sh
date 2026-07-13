#!/usr/bin/env bash
# =====================================================================
# One-time bootstrap of the Google Cloud VM for the Twilio polling bot.
# Does NOT ask for any credentials — those live in GitHub Secrets and are
# written to .env by the deploy workflow (.github/workflows/deploy-gcp.yml)
# on every push. This script only sets up the structure:
#   packages, repo clone, venv, systemd service, and a deploy SSH key.
# At the end it prints the exact GitHub Secrets to add.
#
#   bash setup-twilio-vm.sh
# Safe to re-run.
# =====================================================================
set -euo pipefail

REPO="https://github.com/eliezeravihail/chat.git"
DIR="$HOME/chat"

echo "==> 1/4 system packages"
sudo apt-get update -qq
sudo apt-get install -y -qq git python3 python3-venv python3-pip >/dev/null

echo "==> 2/4 code + virtualenv"
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull --ff-only; else git clone -q "$REPO" "$DIR"; fi
cd "$DIR"
python3 -m venv .venv
./.venv/bin/pip install -q --upgrade pip
./.venv/bin/pip install -q -r requirements.txt

echo "==> 3/4 systemd service (enabled; started by the first deploy)"
sudo tee /etc/systemd/system/wa-bot.service >/dev/null <<EOF
[Unit]
Description=Twilio WhatsApp polling bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=${DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${DIR}/.venv/bin/python ${DIR}/twilio_poll.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable wa-bot.service >/dev/null 2>&1 || true

echo "==> 4/4 deploy SSH key for GitHub Actions"
KEY="$HOME/.ssh/gh_deploy"
mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
[ -f "$KEY" ] || ssh-keygen -t ed25519 -f "$KEY" -N "" -C "github-actions-deploy" >/dev/null
touch "$HOME/.ssh/authorized_keys" && chmod 600 "$HOME/.ssh/authorized_keys"
grep -qxF "$(cat "$KEY.pub")" "$HOME/.ssh/authorized_keys" || cat "$KEY.pub" >> "$HOME/.ssh/authorized_keys"
IP="$(curl -fsS -H 'Metadata-Flavor: Google' \
  http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip 2>/dev/null || true)"

cat <<EOF

============================================================
הוסף ב-GitHub → Settings → Secrets and variables → Actions
→ New repository secret. כל אלה:

  ── חיבור ל-VM ──
  GCP_VM_HOST  = ${IP:-<ה-IP החיצוני של ה-VM מקונסולת גוגל>}
  GCP_VM_USER  = $(whoami)
  GCP_VM_SSH_KEY = הדבק את כל הבלוק הבא (כולל BEGIN/END):
------------------------------------------------------------
$(cat "$KEY")
------------------------------------------------------------

  ── הגדרות הבוט (במקום .env) ──
  OPENROUTER_KEY       = sk-or-...
  TWILIO_ACCOUNT_SID   = AC...
  TWILIO_AUTH_TOKEN    = ...
  TWILIO_FROM          = whatsapp:+14155238886
  ALLOWED_WA_ID        = whatsapp:+9725XXXXXXXX,whatsapp:+9725YYYYYYYY
  (אופציונלי: REDIS_URL, DEFAULT_MODEL)

ואז: git push ל-main (או Actions → deploy-gcp → Run workflow).
הפריסה תכתוב את .env מהסודות ותפעיל את הבוט. כל push הבא — עדכון אוטומטי.
============================================================
EOF
