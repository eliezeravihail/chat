# chat — עוזר WhatsApp חכם בעברית

> ## 🚀 המסלול המומלץ כעת: [Hermes Agent בענן חינמי → HERMES.md](HERMES.md)
> ה-sandbox של Twilio מוגבל ל-**50 הודעות ביום** — לא מעשי לשימוש אמיתי.
> המסלול החדש: סוכן Hermes מלא (זיכרון, כלים, בלי מגבלות) על VM חינמי,
> עם מספר ייעודי. סקריפט הקמה אוטומטי: `hermes/setup-hermes-vm.sh`.
> ההוראות למטה (Twilio) נשארות לבדיקות ולנפחים קטנים.

בוט WhatsApp אישי המחובר למודלי שפה (חינמיים, או Claude / GPT). שיחה טבעית
בעברית, זיכרון שיחה, ושאלות על תמונות. מבוסס **Twilio** — בלי חשבון פייסבוק,
בלי סיכון חסימה, **ובלי שרת או ngrok** (הבוט "שואל" את Twilio על הודעות חדשות).

```
WhatsApp ⇄ Twilio ⇄ twilio_poll.py ⇄ מודל שפה (OpenRouter)
```

שתי דרכים: [מקומי (על המחשב שלך)](#דרך-1--מקומי) או [בענן (תמיד פעיל, 24/7)](#דרך-2--בענן-247).

---

## לפני שמתחילים (משותף לשתי הדרכים)

1. **מפתח OpenRouter** (חינם): <https://openrouter.ai/keys> → **Create Key**.
2. **חשבון Twilio** (חינם — קרדיט ה-trial מספיק, בלי כרטיס אשראי): <https://www.twilio.com/try-twilio>.
3. **הפעל WhatsApp Sandbox:** ב-Console → **Messaging → Try it out → Send a
   WhatsApp message**. תקבל **מספר sandbox** (בד"כ ‎+1 415 523 8886‎ = `TWILIO_FROM`)
   וקוד הצטרפות `join <מילה>`.
4. **כל מי שישתמש בבוט** (המשתמש, וגם אתה לבדיקה) שולח מה-WhatsApp שלו את
   `join <מילה>` אל מספר ה-sandbox — פעם אחת.
5. מהעמוד הראשי ב-Console: **Account SID** ו-**Auth Token**.

צור קובץ `.env` (העתק מ-`.env.example`) ומלא:
```bash
OPENROUTER_KEY=sk-or-...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM=whatsapp:+14155238886
# המספרים שהבוט עונה להם (מופרדים בפסיק). למשל המשתמש + אתה לבדיקה:
ALLOWED_WA_ID=whatsapp:+972500000000,whatsapp:+972526509692
STARTUP_MESSAGE=🤖 הבוט מחובר ומוכן! כתוב לי הודעה ואענה.
```

> הבוט עונה **רק** למספרים ב-`ALLOWED_WA_ID`, ולכל אחד יש זיכרון שיחה נפרד.

---

## דרך 1 — מקומי

על המחשב שלך. צריך **Python 3.11+**.

```bash
git clone https://github.com/eliezeravihail/chat.git
cd chat
python -m pip install -r requirements.txt
copy .env.example .env      # Windows.  ב-mac/linux: cp .env.example .env
```

מלא את `.env` (השדות שלמעלה) ושמור. ואז הרץ:
```bash
python twilio_poll.py
```

זהו! הבוט עולה, שולח הודעת פתיחה, ומגיב תוך 2–4 שניות. ✅
**אין ngrok, אין webhook להגדיר, אין כתובת ציבורית.**
(הבוט חי כל עוד החלון פתוח.)

---

## דרך 2 — בענן (24/7)

כדי שהמשתמש יוכל לדבר עם הבוט **מתי שירצה**, גם כשהמחשב שלך כבוי — הרץ את אותו
סקריפט על VM חינמי. הכי מתאים: **Google Cloud e2-micro** (חינם לתמיד, לא נכבה
בבטלה).

1. <https://console.cloud.google.com> → **Compute Engine → Create instance**.
2. בחר: **Region** `us-central1`, **Machine type** `e2-micro`, **Boot disk**
   Ubuntu 24.04 → **Create**.
3. לחץ על כפתור **SSH** (נפתח טרמינל בדפדפן, על השרת). הרץ בו **פקודה אחת**:

```bash
curl -fsSL https://raw.githubusercontent.com/eliezeravihail/chat/main/setup-twilio-vm.sh -o setup.sh && bash setup.sh
```

הסקריפט מתקין הכל, שואל את 4 הערכים (מפתח OpenRouter, ‏Account SID, ‏Auth Token,
המספרים המורשים), ומריץ את הבוט כ**שירות systemd** — רץ 24/7, עולה מחדש בקריסה
או ריסטארט, בלי tmux. פקודות: `journalctl -u wa-bot -f` (לוגים),
`sudo systemctl restart wa-bot` (הפעלה מחדש).

**אין צורך בפתיחת פורטים, HTTPS או webhook** — ה-polling הוא חיבור יוצא בלבד.

> **למה Google?** Oracle מכבה מכונות בטלות (הבוט שלנו בטל רוב הזמן), ו-AWS/Azure
> כבר לא מציעים VM חינמי לתמיד. e2-micro חינמי לתמיד ולא נכבה.

### עדכון אוטומטי מ-GitHub (push → נפרס ל-VM לבד)

כדי שכל שינוי קוד ייפרס ל-VM אוטומטית, בלי SSH ידני: הרץ **פעם אחת** על ה-VM
```bash
bash ~/chat/enable-autodeploy.sh
```
הוא מייצר מפתח deploy ומדפיס שלושה ערכים. הוסף אותם ב-**GitHub → Settings →
Secrets and variables → Actions → New repository secret**:
`GCP_VM_HOST`, `GCP_VM_USER`, `GCP_VM_SSH_KEY`. מעכשיו כל `git push` ל-`main`
מתחבר ל-VM, מושך את הקוד ומפעיל מחדש את השירות (הזרימה:
`.github/workflows/deploy-gcp.yml`).

---

## דרך 3 — Fly.io עם עדכון אוטומטי מ-GitHub (push → מתעדכן לבד)

רוצה שהבוט ירוץ בענן **וגם יתעדכן אוטומטית** בכל שינוי קוד, בלי לגעת בשרת? הבוט
מתארח ב-Fly (worker קבוע, בלי webhook), ו-GitHub Action פורס אותו בכל push ל-`main`.

**הקמה חד-פעמית:**
```bash
curl -L https://fly.io/install.sh | sh
fly auth login
fly launch --no-deploy                 # בחר שם אפליקציה; עדכן app ב-fly.toml
fly secrets set \
  OPENROUTER_KEY=... TWILIO_ACCOUNT_SID=... TWILIO_AUTH_TOKEN=... \
  TWILIO_FROM="whatsapp:+14155238886" ALLOWED_WA_ID="whatsapp:+9725XXXXXXXX"
fly deploy                             # פריסה ראשונה

fly tokens create deploy               # העתק את הטוקן
```
ואז ב-**GitHub → Settings → Secrets and variables → Actions → New repository secret**:
שם `FLY_API_TOKEN`, ערך = הטוקן.

מעכשיו — **כל push ל-`main` פורס אוטומטית** את הקוד העדכני (הזרימה מוגדרת ב-
`.github/workflows/fly-deploy.yml`). זה בדיוק "להריץ קוד עדכני בקלות", במקום
לגיטימי — לא לולאה ב-Actions (שאסורה ומוגבלת ל-6 שעות), אלא פריסה ל-worker קבוע.

---

## פקודות (בתוך הצ'אט)

| פקודה | פעולה |
| --- | --- |
| `/model <שם>` | החלפת מודל: `claude`, `gpt`, `gemini`, `deepseek`, `llama`, `qwen` |
| `/models` | רשימת המודלים והנוכחי |
| `/clear` | ניקוי הזיכרון |

**ברירת המחדל: `tencent/hy3`** — ואם נגמר הקרדיט (או תקלה), הבוט נופל אוטומטית
למודלים החינמיים 🆓 ומודיע. לשינוי ברירת המחדל: `DEFAULT_MODEL` ב-`.env`
(סלאג/כינוי, או `auto` לחינמי בלבד). שליחת **תמונה** → הבוט מנתח אותה.

---

## הערות

- **זיכרון מתמשך:** בברירת מחדל הזיכרון נמחק כשעוצרים את הסקריפט. לזיכרון של 30
  יום חבר Redis חינם מ-<https://upstash.com> — הוסף ל-`.env`:
  `REDIS_URL=rediss://...`.
- **הודעת פתיחה** מגיעה רק למספר ששלח `join` + הודעה ב-24 השעות האחרונות (חוק של
  WhatsApp). הסדר: כולם שולחים `join`, ואז מריצים את הסקריפט.
- **Sandbox** = סביבת הבדיקה של Twilio (הגבלת קצב קלה; מספיק לשימוש אישי). למספר
  ייעודי משלך צריך Sender בתשלום ב-Twilio.
- **רוצה תגובה מיידית** (בלי 2–4 שניות)? יש גם מצב **webhook** (`twilio_bot.py`
  עם ngrok/Fly.io) — דורש כתובת ציבורית. ראה `.env.example`.

<sub>הקוד כולל גם מתאמי **Baileys** (מקומי, מספר משלך) ו-**Meta Cloud API** רשמי —
`baileys/`, `wa_bot.py`. לא נדרשים לשתי הדרכים שלמעלה.</sub>

## רישיון

[MIT](LICENSE) © 2026 Eliezer Avihail
