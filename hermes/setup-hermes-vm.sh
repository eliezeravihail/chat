#!/usr/bin/env bash
# =====================================================================
# One-shot Hermes Agent bootstrap for a fresh Ubuntu 24.04 VM — x86 or ARM
# (Oracle Cloud Always Free Ampere A1, or GCP e2-micro). Sets up EVERYTHING
# except the WhatsApp QR scan:
#   swap (small machines only), deps, hermes-agent install, OpenRouter + HY3 +
#   free fallbacks, Groq voice-note transcription, encrypted ~/.hermes,
#   Hebrew persona (SOUL.md), WhatsApp whitelist, gateway user service.
#
# Usage (all on one line, fill in your values):
#   OPENROUTER_KEY=sk-or-... GROQ_KEY=gsk_... HERMES_MEMORY_KEY=<same as the \
#     GitHub secret> ALLOWED_NUMBERS=972526509692,972527204725 bash setup-hermes-vm.sh
#
# Or just run `bash setup-hermes-vm.sh` and answer the prompts.
#   GROQ_KEY          optional — free key from console.groq.com; enables Hebrew
#                     transcription of voice notes (stt.provider: groq).
#   HERMES_MEMORY_KEY optional but RECOMMENDED — the encryption key for the
#                     memory store. Generate once (`openssl rand -base64 32`),
#                     save it as the GitHub secret HERMES_MEMORY_KEY, and pass
#                     the same value here so backups made by the CI can be
#                     restored on a new machine. Omitted = a random key is
#                     generated on this VM only (backups die with the VM).
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
GROQ_KEY="${GROQ_KEY:-}"

# Hermes needs Python >= 3.11 (Ubuntu 24.04 ships 3.12; 22.04 ships 3.10 — too old).
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
  echo "python3 >= 3.11 required — use an Ubuntu 24.04 image." >&2
  exit 1
fi

echo "==> 1/7 swap (2G) — only on small machines (<4GB RAM)"
MEM_KB="$(awk '/MemTotal/{print $2}' /proc/meminfo)"
if [ "${MEM_KB:-0}" -ge 4000000 ]; then
  echo "    ${MEM_KB}kB RAM — no swap needed, skipping"
elif ! swapon --show | grep -q /swapfile; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
else
  echo "    swap already active — skipping"
fi

echo "==> 2/7 system packages"
sudo apt-get update -qq
# psmisc (fuser) + lsof: the CI frees port 3000 by port, never by name.
# ffmpeg: Hermes trims silence from voice notes before uploading them for STT.
sudo apt-get install -y -qq python3-venv python3-pip curl gocryptfs fuse3 psmisc lsof ffmpeg >/dev/null

echo "==> 3/7 hermes-agent (venv at ~/hermes-env)"
if [ ! -d "$HOME/hermes-env" ]; then
  python3 -m venv "$HOME/hermes-env"
fi
"$HOME/hermes-env/bin/pip" install -q --upgrade pip
"$HOME/hermes-env/bin/pip" install -q --upgrade hermes-agent
grep -q 'hermes-env/bin' "$HOME/.bashrc" || echo 'export PATH="$HOME/hermes-env/bin:$PATH"' >> "$HOME/.bashrc"
export PATH="$HOME/hermes-env/bin:$PATH"

echo "==> 4/7 encrypted data store (gocryptfs)"
# Hermes always writes conversation transcripts to ~/.hermes/state.db (plaintext
# by default). We keep ~/.hermes as a gocryptfs mount so the FILES on disk are
# ciphertext; decryption is lazy, per-file, in memory only while mounted. The
# key lives in a 0600 file on the VM — this satisfies "no plaintext conversation
# files at rest", not anti-theft (that would need an off-machine key).
HH="${HERMES_HOME:-$HOME/.hermes}"
KEYFILE="$HOME/.hermes.key"
CIPHER="$HOME/.hermes.cipher"
if [ ! -f "$KEYFILE" ]; then
  if [ -n "${HERMES_MEMORY_KEY:-}" ]; then printf '%s' "$HERMES_MEMORY_KEY" > "$KEYFILE"
  else openssl rand -base64 32 > "$KEYFILE"; fi
  chmod 600 "$KEYFILE"
fi
# let the hermes service (whatever user it runs as) read the FUSE mount
grep -q '^user_allow_other' /etc/fuse.conf 2>/dev/null || echo 'user_allow_other' | sudo tee -a /etc/fuse.conf >/dev/null
mkdir -p "$CIPHER" "$HH"
[ -f "$CIPHER/gocryptfs.conf" ] || gocryptfs -init -passfile "$KEYFILE" "$CIPHER"
mountpoint -q "$HH" || gocryptfs -allow_other -passfile "$KEYFILE" "$CIPHER" "$HH"
# auto-mount on boot, before the hermes gateway
sudo tee /etc/systemd/system/hermes-crypt.service >/dev/null <<UNIT
[Unit]
Description=Mount encrypted Hermes store (gocryptfs)
After=local-fs.target
Before=hermes-gateway.service
[Service]
Type=oneshot
RemainAfterExit=yes
User=$(whoami)
ExecStart=/usr/bin/gocryptfs -allow_other -passfile $KEYFILE $CIPHER $HH
ExecStop=/bin/fusermount -u $HH
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable hermes-crypt >/dev/null 2>&1 || true

echo "==> 5/7 hermes config (model, fallbacks, key, whitelist, voice notes, Hebrew persona)"
mkdir -p "$HH"   # now the decrypted (mounted) view

# Primary model + free fallback chain. Edit freely — `hermes fallback list`
# shows the effective chain. Free slugs rot; replace with any current ones.
#
# SECURITY: the empty allowlists below aim for pure language-model chat, but we
# ALSO set `agent.disabled_toolsets` — a global denylist that wins over every
# allowlist and default. This is critical on a MULTI-USER bot: the built-in
# `session_search` and `memory` toolsets search/recall across ALL stored
# sessions with NO per-user filter, so if they were ever active one person's
# data could surface in another's chat. The denylist forces them off for good.
# `browser`/`spotify`/`web` are heavy/irrelevant and kept off too.
cat > "$HH/config.yaml" <<EOF
model: ${PRIMARY_MODEL}
# Per-user memory isolation. Each WhatsApp DM is keyed by phone number and each
# group message by participant, so one person's conversation/memory never bleeds
# into another's. 'true' is Hermes' default; we pin it so a hand-edit can't turn
# privacy off silently (critical for a therapy bot with more than one user).
group_sessions_per_user: true
thread_sessions_per_user: false
agent:
  # Global denylist — removes these toolsets on every channel, beating any
  # allowlist. session_search + memory are the privacy-critical ones (they read
  # across all users' sessions). Conversation continuity is NOT affected: the
  # ongoing transcript is part of the session, not the 'memory' toolset.
  disabled_toolsets: [session_search, memory, browser, spotify, web]
fallback_providers:
  - provider: openrouter
    model: meta-llama/llama-3.3-70b-instruct:free
  - provider: openrouter
    model: qwen/qwen3-next-80b-a3b-instruct:free
platform_toolsets:
  whatsapp: []
  cli: []
toolsets: []
# Voice notes → text. Inbound WhatsApp voice messages are transcribed and fed to
# the model as text; echo_transcripts also posts the raw transcript back to the
# chat (🎙️ "…"), so a voice note sent to the bot comes back as readable text.
# Groq's Whisper is free-tier and good at Hebrew (full large-v3, not turbo).
# Needs GROQ_API_KEY in .env; without it voice notes get a "could not be
# transcribed" marker. Never 'local' here — Whisper that handles Hebrew well
# needs a strong CPU/GPU and would choke a free-tier VM.
stt:
  enabled: true
  echo_transcripts: true
  provider: groq
  language: he
  groq:
    model: whisper-large-v3
    language: he
# NOTE: do NOT set whatsapp.group_policy: open — Hermes refuses to start the
# gateway under an 'open' policy unless WHATSAPP_ALLOW_ALL_USERS is enabled
# (which would answer everyone). For group responses use group_policy: allowlist
# with a specific group JID instead.
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
if [ -n "$GROQ_KEY" ]; then
  grep -q '^GROQ_API_KEY=' "$HH/.env" 2>/dev/null \
    && sed -i "s|^GROQ_API_KEY=.*|GROQ_API_KEY=${GROQ_KEY}|" "$HH/.env" \
    || echo "GROQ_API_KEY=${GROQ_KEY}" >> "$HH/.env"
else
  echo "    (no GROQ_KEY — voice notes won't be transcribed until GROQ_API_KEY is set)"
fi

# Hebrew persona (Aharon). Single source of truth is SOUL.md in the repo — fetch
# it so the deployed persona never drifts. Minimal fallback if the download fails.
if ! curl -fsSL https://raw.githubusercontent.com/eliezeravihail/chat/main/SOUL.md -o "$HH/SOUL.md"; then
  echo "    (couldn't fetch SOUL.md — writing a minimal fallback persona)"
  cat > "$HH/SOUL.md" <<'EOF'
# מי אתה
אתה אהרון — פסיכותרפיסט חם ומקצועי שמלווה בשיחה בוואטסאפ, בעברית ובגוף ראשון זכר.
הקשב, הכל ותמוך; אל תמהר לפרש או לכוון — קודם בונים אמון. אינך מטפל מוסמך ולא
תחליף לטיפול; במצוקה חריפה הפנה לעזרה: ער"ן 1201, מד"א 101 או משטרה 100. אל
תנהל שיחות ארוטיות/מיניות. עיצוב וואטסאפ בלבד, קצר ואנושי.
EOF
fi

echo "==> 6/7 non-Python deps (node for the WhatsApp bridge, etc.) + gateway service"
hermes postinstall || true
# The gateway runs as a systemd *user* service (what the CI restarts). Install the
# unit now (it is NOT started here — start it after the QR pairing) and enable
# linger so it keeps running after you log out and comes back after a reboot.
sudo loginctl enable-linger "$(whoami)" 2>/dev/null || true
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
systemctl --user cat hermes-gateway >/dev/null 2>&1 || hermes gateway install >/dev/null 2>&1 || true

echo "==> 7/7 verify"
hermes fallback list || true
echo
echo "============================================================"
echo "✅ ההקמה הושלמה. נשארו רק שני צעדים ידניים:"
echo
echo "1) חיבור WhatsApp + הפעלת השירות, בפקודה אחת ובסדר הנכון:"
echo "     bash ~/chat/hermes/setup-hermes-vm.sh   ← (כבר רץ)"
echo "     bash ~/chat/hermes/repair-whatsapp.sh   ← יוצג QR; סרוק מיד מהטלפון של מספר הבוט"
echo "        (מכשירים מקושרים ← קשר מכשיר). אחרי 'Pairing complete' השירות עולה לבד."
echo "     ואז 5 דקות לא נוגעים בכלום (בלי restart / Ctrl+C)."
echo
echo "2) אחרי 5 דקות: שלח הודעה לבוט מהמספר שלך."
echo "     systemctl --user is-active hermes-gateway   ← צריך להיות active"
echo
echo "שימושי: hermes status | hermes logs | hermes model | hermes fallback list"
echo
echo "🔒 הזיכרון מוצפן: ~/.hermes הוא gocryptfs (ciphertext ב-~/.hermes.cipher,"
echo "   מפתח ב-~/.hermes.key). מותקן אוטומטית באתחול (שירות hermes-crypt)."
echo "============================================================"
