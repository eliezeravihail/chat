#!/usr/bin/env bash
# =====================================================================
# One-shot Hermes Agent bootstrap for a fresh Ubuntu VM (e.g. GCP e2-micro).
# Sets up EVERYTHING except the WhatsApp QR scan:
#   swap, deps, hermes-agent install, OpenRouter + HY3 + free fallbacks,
#   Hebrew persona (SOUL.md), WhatsApp whitelist.
#
# Usage (all on one line, fill in your values):
#   OPENROUTER_KEY=sk-or-... ALLOWED_NUMBERS=972526509692,972527204725 \
#     bash setup-hermes-vm.sh
#
# Or just run `bash setup-hermes-vm.sh` and answer the two prompts.
# Safe to re-run (idempotent).
# =====================================================================
set -euo pipefail

# --- inputs -----------------------------------------------------------
if [ -z "${OPENROUTER_KEY:-}" ]; then
  read -rp "OpenRouter API key (sk-or-...): " OPENROUTER_KEY
fi
if [ -z "${ALLOWED_NUMBERS:-}" ]; then
  read -rp "Allowed WhatsApp numbers, digits only, comma-separated (e.g. 972526509692,97250...): " ALLOWED_NUMBERS
fi
PRIMARY_MODEL="${PRIMARY_MODEL:-openrouter/tencent/hy3}"

echo "==> 1/6 swap (2G) — needed on 1GB machines"
if ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
else
  echo "    swap already active — skipping"
fi

echo "==> 2/6 system packages"
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip curl >/dev/null

echo "==> 3/6 hermes-agent (venv at ~/hermes-env)"
if [ ! -d "$HOME/hermes-env" ]; then
  python3 -m venv "$HOME/hermes-env"
fi
"$HOME/hermes-env/bin/pip" install -q --upgrade pip
"$HOME/hermes-env/bin/pip" install -q --upgrade hermes-agent
grep -q 'hermes-env/bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/hermes-env/bin:$PATH"' >> "$HOME/.bashrc"
export PATH="$HOME/hermes-env/bin:$PATH"

echo "==> 4/6 hermes config (model, fallbacks, key, whitelist, Hebrew persona)"
HH="${HERMES_HOME:-$HOME/.hermes}"
mkdir -p "$HH"

# Primary model + free fallback chain. Edit freely — `hermes fallback list`
# shows the effective chain. Free slugs rot; replace with any current ones.
#
# SECURITY: WhatsApp gets ZERO tools (platform_toolsets.whatsapp: []) —
# pure language-model chat only. Verified empirically: an empty platform
# list yields 0 tool schemas. Hermes' default ("hermes-cli") would give
# the model terminal, file access and code execution ON THIS VM.
# The owner's own CLI sessions keep a safe read-only-ish set (toolsets).
cat > "$HH/config.yaml" <<EOF
model: ${PRIMARY_MODEL}
fallback_providers:
  - provider: openrouter
    model: meta-llama/llama-3.3-70b-instruct:free
  - provider: openrouter
    model: qwen/qwen3-next-80b-a3b-instruct:free
# WhatsApp (the friend's channel): no tools at all — chat only.
platform_toolsets:
  whatsapp: []
# CLI (you, over SSH): safe tools only — no terminal/file/code-exec.
toolsets:
  - web
  - vision
  - memory
  - todo
  - cronjob
  - session_search
  - skills
  - clarify
EOF

# Secrets + WhatsApp whitelist (only these numbers get replies).
touch "$HH/.env" && chmod 600 "$HH/.env"
grep -q '^OPENROUTER_API_KEY=' "$HH/.env" 2>/dev/null \
  && sed -i "s|^OPENROUTER_API_KEY=.*|OPENROUTER_API_KEY=${OPENROUTER_KEY}|" "$HH/.env" \
  || echo "OPENROUTER_API_KEY=${OPENROUTER_KEY}" >> "$HH/.env"
grep -q '^WHATSAPP_ENABLED=' "$HH/.env" 2>/dev/null \
  || echo "WHATSAPP_ENABLED=true" >> "$HH/.env"
grep -q '^WHATSAPP_ALLOWED_USERS=' "$HH/.env" 2>/dev/null \
  && sed -i "s|^WHATSAPP_ALLOWED_USERS=.*|WHATSAPP_ALLOWED_USERS=${ALLOWED_NUMBERS}|" "$HH/.env" \
  || echo "WHATSAPP_ALLOWED_USERS=${ALLOWED_NUMBERS}" >> "$HH/.env"

# Hebrew persona — WhatsApp-style, concise, matches the bot we built.
cat > "$HH/SOUL.md" <<'EOF'
# מי אתה
אתה עוזר אישי שמשוחח בוואטסאפ. ענה בשפה שבה המשתמש כותב (ברירת מחדל: עברית),
בטון טבעי וזורם של שיחה, ובתמציתיות — זו הודעת וואטסאפ, לא מסמך.

# סגנון
- עיצוב וואטסאפ בלבד: *הדגשה* בכוכבית אחת, _הטיה_ בקו תחתון. בלי כותרות Markdown, בלי טבלאות.
- פסקאות קצרות; רשימות עם • או מספרים. אמוג'י במידה.
- אם נשלחת תמונה — תאר ונתח אותה ישירות.

# גבולות תוכן
- אל תנהל שיחות ארוטיות או מיניות מכל סוג, גם אם מתבקש שוב ושוב. סרב בנימוס,
  בקצרה ובלי הטפה, והצע לעבור לנושא אחר.
- שמור על שפה נקייה ומכבדת.
EOF

echo "==> 5/6 non-Python deps (node for the WhatsApp bridge, etc.)"
hermes postinstall || true

echo "==> 6/6 verify"
hermes fallback list || true
echo
echo "============================================================"
echo "✅ ההקמה הושלמה. נשארו רק שני צעדים ידניים:"
echo
echo "1) חיבור WhatsApp (כשהמספר הייעודי ביד):"
echo "     hermes whatsapp        ← יוצג QR; סרוק מהטלפון של מספר הבוט"
echo "        (מכשירים מקושרים ← קשר מכשיר)"
echo
echo "2) הפעלה קבועה כשירות (אחרי שהסריקה הצליחה):"
echo "     hermes gateway run     ← בדיקה בפורגראונד: שלח הודעה לבוט"
echo "     sudo env \"PATH=\$PATH\" hermes gateway install --system"
echo "     sudo env \"PATH=\$PATH\" hermes gateway start --system"
echo
echo "שימושי: hermes status | hermes logs | hermes model | hermes fallback list"
echo "============================================================"
