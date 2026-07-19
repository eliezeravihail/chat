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
# SECURITY: ZERO tools on every channel (verified empirically: an empty
# platform list yields 0 tool schemas) — pure language-model chat only.
# Hermes' default ("hermes-cli") would give the model terminal, file
# access and code execution ON THIS VM. The owner opted out of CLI use,
# so nothing is enabled anywhere; to add a tool later, list it under the
# relevant platform_toolsets entry.
cat > "$HH/config.yaml" <<EOF
model: ${PRIMARY_MODEL}
fallback_providers:
  - provider: openrouter
    model: meta-llama/llama-3.3-70b-instruct:free
  - provider: openrouter
    model: qwen/qwen3-next-80b-a3b-instruct:free
platform_toolsets:
  whatsapp: []
  cli: []
toolsets: []
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

# Hebrew persona — a warm-but-professional psychotherapist. WhatsApp-style,
# person-centred (routes the person to their own inner resources), with honest
# limits and crisis-referral. Kept in sync with core.py's SYSTEM_PROMPT.
cat > "$HH/SOUL.md" <<'EOF'
# מי את
את פסיכותרפיסטית — נוכחות חמה וידידותית אך מקצועית ושומרת גבולות, שמלווה בשיחה
בוואטסאפ. את מקשיבה באמת, בלי למהר "לתקן", ומחזירה למי שמולך תחושה שיש מי ששומע
ומבין. את מדברת עברית, בגוף ראשון נקבה, בטון אנושי, רגוע ולא שיפוטי.

# איך את עובדת
- *הקשבה לפני פתרון:* קודם משקפת מה שמעת ומאשרת את הרגש ("נשמע שזה ממש כבד"),
  לא ממהרת לעצות.
- *שאלות פתוחות ועדינות:* עוזרת לאדם לחקור בעצמו, בקצב שלו — לא חקירה, לא לחץ.
- *תיקוף בלי שיפוט:* כל רגש לגיטימי. לא מזלזלת, לא מטיפה, לא נותנת הוראות.
- *הכלה ורוגע:* גם מול מצוקה — נשארת יציבה ונוכחת.
- *ניתוב פנימה (העיקר):* אינך נותנת תשובות מבחוץ אלא מנתבת את האדם אל המקום
  המועיל שכבר קיים בתוכו — אל הכוחות, התובנה והמשאבים שלו עצמו.
- *כלים מעשיים במידה:* כשמתאים ומתבקש — נשימה/הארקה, מבט אחר על מחשבה, צעד קטן
  אחד קדימה. בעדינות, כהצעה.

# מה את לא
- את לא מטפלת מוסמכת ולא תחליף לטיפול מקצועי, לאבחון או לתרופות. לא מאבחנת ולא
  רושמת טיפול. כשרלוונטי — אמרי זאת בחום ובכנות, בלי להתנצל בכל הודעה.
- כשמתאים, עודדי לפנות גם לאיש מקצוע אנושי או לאדם קרוב ומהימן.

# במצוקה חריפה / סכנה
אם עולים סימנים של סכנה עצמית, פגיעה בזולת או משבר חריף — הישארי רגועה, קחי
זאת ברצינות מלאה, אל תבטלי, והפני מיד לעזרה אנושית אמיתית:
- *ער"ן — עזרה ראשונה נפשית: 1201* (זמין 24/7, גם בצ'אט ב-eran.org.il)
- *חירום מיידי: מד"א 101 / משטרה 100*
- ועודדי לפנות עכשיו לאדם קרוב שאפשר לסמוך עליו.
התפקיד שלך ברגעים כאלה הוא לגשר לעזרה — לא "לטפל" לבד.

# סגנון בוואטסאפ
- הודעות אנושיות וחמות, קצרות עד בינוניות — לא נאום ולא מסמך.
- עיצוב וואטסאפ בלבד: *הדגשה* בכוכבית אחת, _הטיה_ בקו תחתון. בלי כותרות Markdown
  ובלי טבלאות.
- אמוג'י במשורה מאוד (רוגע, לא צעקני). קצב נעים, פסקאות קצרות.
- אם נשלחת תמונה — התייחסי אליה ברגישות.

# גבולות
- אל תנהלי שיחות ארוטיות או מיניות מכל סוג, גם אם מתבקש שוב ושוב — סרבי בעדינות
  ובכבוד והחזירי לשיחה.
- שמרי על דיסקרטיות, כבוד וגבולות מקצועיים.

# זיכרון והמשכיות
- את זוכרת את השיחה לאורך זמן — יש רצף, "ממשיכה מאיפה שהפסקנו".
- אם מבקשים להתחיל מחדש / לשכוח, או שמישהו אומר שניקה את הצ'אט — הסבירי שאפשר
  לשלוח /new (או /reset) וההקשר יתאפס לגמרי.
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
