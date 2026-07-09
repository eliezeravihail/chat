# chat — גשר WhatsApp ⇄ OpenRouter

בוט שמחבר את **WhatsApp** אל **OpenRouter**, ומאפשר לשוחח עם מודלי שפה
(Claude / GPT / Gemini / מודלים חינמיים) ישירות מצ'אט וואטסאפ — שיחה טבעית
בעברית, עם זיכרון ושאלות על תמונות. הבוט נעול ל**משתמש מורשה יחיד**.

```
WhatsApp → Twilio → Webhook (FastAPI) → OpenRouter → תשובה חזרה
```

יש **שלושה מתאמים**, כולם חולקים את אותה ליבה (`core.py`):

| מתאם | קובץ | פייסבוק? | הערה |
| --- | --- | :---: | --- |
| **Twilio** (ברירת מחדל בענן) | `twilio_bot.py` | ❌ | הכי פשוט לענן |
| **Baileys** (מקומי) | `baileys/` + `local_server.py` | ❌ | ללא ספק חיצוני; מספר אישי דרך QR — ראה [נספח B](#נספח-b--הרצה-מקומית-עם-baileys-ללא-פייסבוק-ללא-twilio) |
| **Meta Cloud API** | `wa_bot.py` | ✅ | הרשמי — ראה [נספח A](#נספח-a--meta-cloud-api) |

המדריך הראשי מתמקד ב-**Twilio**. להרצה מקומית מלאה ללא שום ספק חיצוני — **נספח B**.

---

## תוכן עניינים

1. [OpenRouter — מפתח API](#1-openrouter--מפתח-api)
2. [Twilio — הקמת WhatsApp](#2-twilio--הקמת-whatsapp)
3. [הרצה מקומית](#3-הרצה-מקומית)
4. [פריסה לענן (Fly.io)](#4-פריסה-לענן-flyio)
5. [זיכרון מתמשך (Upstash Redis)](#5-זיכרון-מתמשך-upstash-redis)
6. [שימוש ופקודות](#6-שימוש-ופקודות)
7. [פתרון תקלות](#7-פתרון-תקלות)
8. [משתני סביבה](#8-משתני-סביבה)
- [נספח A — Meta Cloud API](#נספח-a--meta-cloud-api)

> **הערה על מדיניות Meta (ינואר 2026):** תנאי ה-WhatsApp Business API אוסרים
> צ'אטבוטים כלליים של AI כ"פונקציונליות עיקרית" (זו הסיבה ש-1-800-ChatGPT נסגר).
> זה חל גם על Twilio (שרץ מעל התשתית של Meta) וגם על Meta ישירות. בוט אישי בנפח
> זעיר למשתמש יחיד — סבירות אכיפה נמוכה, אך קיים סיכון תיאורטי לחסימה. מומלץ נפח
> נמוך ולא לפרסם את המספר. חלופה ללא איסור דומה: Telegram Bot API (אותה ליבה).

---

## 1. OpenRouter — מפתח API

1. היכנס ל-<https://openrouter.ai> והתחבר.
2. גש ל-<https://openrouter.ai/keys> → **Create Key**.
3. העתק את המפתח — זה הערך של `OPENROUTER_KEY`.

מודלים עם סיומת `:free` (DeepSeek, Llama, Qwen, Gemini Flash) ללא עלות. כדי
להשתמש ב-Claude / GPT צריך להטעין קרדיט קטן בחשבון OpenRouter.

---

## 2. Twilio — הקמת WhatsApp

### 2.1 חשבון ופרטים
1. פתח חשבון ב-<https://www.twilio.com/try-twilio> (ללא פייסבוק).
2. ב-<https://console.twilio.com> תמצא בעמוד הראשי:
   - **Account SID** → `TWILIO_ACCOUNT_SID`
   - **Auth Token** → `TWILIO_AUTH_TOKEN`

### 2.2 הפעלת WhatsApp Sandbox
1. ב-Console: **Messaging → Try it out → Send a WhatsApp message**.
2. תקבל מספר sandbox (בד"כ `+1 415 523 8886`) וקוד הצטרפות (`join <word>`).
   המספר הזה הוא `TWILIO_FROM` בפורמט `whatsapp:+14155238886`.
3. מהוואטסאפ שלך, שלח `join <word>` למספר ה-sandbox. מהרגע הזה המספר שלך מחובר
   ל-sandbox (צריך לחזור על זה אם עוברים 72 שעות ללא פעילות).
4. המספר שלך, למשל `whatsapp:+9725XXXXXXXX`, הוא `ALLOWED_WA_ID`.

> **פרודקשן:** למספר ייעודי ללא הגבלת ה-sandbox צריך WhatsApp Sender מאושר
> ב-Twilio (כרוך בתשלום per-message). ה-sandbox מספיק למשתמש יחיד.

---

## 3. הרצה מקומית

```bash
git clone https://github.com/eliezeravihail/chat.git
cd chat
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # ערוך את הערכים (Twilio + OpenRouter)
set -a; source .env; set +a

uvicorn twilio_bot:app --host 0.0.0.0 --port 8080
```

בדיקה: `curl http://localhost:8080/health` → `{"status":"ok"}`

כדי ש-Twilio יגיע ל-webhook המקומי, חשוף אותו עם tunnel והגדר `PUBLIC_URL`:
```bash
ngrok http 8080          # העתק את כתובת ה-https
export PUBLIC_URL=https://<ngrok-id>.ngrok-free.app
```
ואז ב-**Twilio Console → Sandbox settings → "When a message comes in"**:
`https://<ngrok-id>.ngrok-free.app/webhook` (method **POST**).

---

## 4. פריסה לענן (Fly.io)

הפרויקט כולל `Dockerfile` ו-`fly.toml` (ברירת מחדל: `twilio_bot`).

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
fly launch --no-deploy               # בחר שם ייחודי; עדכן app ב-fly.toml

fly secrets set \
  TWILIO_ACCOUNT_SID=... \
  TWILIO_AUTH_TOKEN=... \
  TWILIO_FROM="whatsapp:+14155238886" \
  ALLOWED_WA_ID="whatsapp:+9725XXXXXXXX" \
  PUBLIC_URL="https://<app-name>.fly.dev" \
  OPENROUTER_KEY=...

fly deploy
```

לבסוף, הצבע את ה-webhook של Twilio (שלב 2.2) אל
`https://<app-name>.fly.dev/webhook`.

> אלטרנטיבה: יש גם `Procfile` ל-**Render / Railway**. המשתנה `APP_MODULE`
> בוחר מתאם (`twilio_bot:app` ברירת מחדל, או `wa_bot:app` ל-Meta).

---

## 5. זיכרון מתמשך (Upstash Redis)

וואטסאפ שולח רק את ההודעה **החדשה** בכל פעם, לכן הבוט שומר את היסטוריית השיחה.
בברירת מחדל הזיכרון נשמר בזיכרון התהליך (נמחק ב-restart/redeploy). כדי **להמשיך
שיחה בכל זמן**, חבר Redis:

1. חשבון חינם ב-<https://upstash.com> → **Create Database** (Redis).
2. העתק את ה-`redis://` / `rediss://` URL.
3. `fly secrets set REDIS_URL="rediss://default:<password>@<host>:<port>"`

עם `REDIS_URL` מוגדר: היסטוריה תחת `hist:{id}` (TTL 30 יום), מודל תחת
`model:{id}`, ודה-דופליקציה תחת `seen:{id}`. בלעדיו — זיכרון פנימי. בהפעלה
מודפס בלוג `state backend: RedisStore` או `MemoryStore`.

---

## 6. שימוש ופקודות

שלח הודעת WhatsApp מהמספר המורשה — תקבל תשובה מהמודל.

| פקודה | פעולה |
| --- | --- |
| `/models` | רשימת המודלים והמודל הנוכחי |
| `/model <שם>` | החלפת מודל (מאפס הקשר) |
| `/model` | הצגת המודל הנוכחי |
| `/clear` | ניקוי היסטוריית השיחה |

**Aliases:** `claude`, `gpt`, `gemini`, `deepseek`, `llama`, `qwen`, או מזהה
OpenRouter מלא (`/model anthropic/claude-sonnet-4.5`).

### קריאת תמונות (Vision)
שליחת תמונה (עם/בלי כיתוב) — הבוט מוריד אותה ושולח למודל ראייה. כיתוב ריק →
שאלת ברירת מחדל ("מה רואים בתמונה?"). בהיסטוריה נשמר רק סמן `[תמונה]`, לא ה-blob.
*יצירת* תמונות אינה נתמכת — קריאה בלבד.

### מעבר אוטומטי בין מודלים
ברירת המחדל חינמית (`deepseek`). כשהמודל המועדף לא זמין (מכסה / rate-limit /
תקלה), הבוט עונה **באותו תור** עם המודל הבא ומודיע — אך **לא מחליף את ההעדפה**,
כך שתקלה רגעית לא מורידה אותך לצמיתות. שרשראות:
- טקסט: `deepseek → llama → qwen → gemini`
- ראייה: `claude/gpt (אם מועדף) → gemini → llama-3.2-vision → qwen-vl`

מודל שהוצא משימוש פשוט מחזיר שגיאה והלולאה ממשיכה — השרשרת מרפאת את עצמה.

### שיחה טבעית
- **System prompt** מכוון לעברית, לתמציתיות ולפורמט וואטסאפ.
- **המרת Markdown** אוטומטית (`**`→`*`, כותרות→מודגש, `-`→`•`).
- **זיכרון 30 יום / 40 הודעות**.
- **דה-דופליקציה** — כל הודעה מטופלת פעם אחת (Twilio/Meta מוסרים at-least-once).
- **"מקליד..." + וי כחול** — במתאם Meta בלבד (Twilio לא חושף API לזה).

---

## 7. פתרון תקלות

| תסמין | סיבה סבירה | פתרון |
| --- | --- | --- |
| `403 bad signature` בלוגים | `PUBLIC_URL` לא תואם ל-URL האמיתי | ודא ש-`PUBLIC_URL` זהה לכתובת שהוגדרה ב-Twilio (כולל https, בלי `/` בסוף) |
| אין תשובה בכלל | המספר לא ב-whitelist | ודא ש-`ALLOWED_WA_ID` הוא בדיוק המספר ששולח |
| "join again" מ-Twilio | פג תוקף ה-sandbox | שלח שוב `join <word>` למספר ה-sandbox |
| התמונה לא נקראת | המודל הנוכחי לא vision | תמונות עוברות אוטומטית ל-gemini; אם עדיין נכשל, נסה `/model gemini` |
| היסטוריה נמחקת ב-restart | מצב in-memory | חבר `REDIS_URL` (שלב 5) |
| הבוט "שכח" באמצע | חריגת אורך במודל חינמי | הורד `HISTORY_TURNS` ב-`core.py` או עבור למודל גדול יותר |

---

## 8. משתני סביבה

ראה `.env.example`. סיכום (מתאם Twilio):

| משתנה | חובה | תיאור |
| --- | :---: | --- |
| `TWILIO_ACCOUNT_SID` | ✅ | Account SID מ-Twilio Console |
| `TWILIO_AUTH_TOKEN` | ✅ | Auth Token (גם ל-REST וגם לאימות חתימה) |
| `TWILIO_FROM` | ✅ | מספר השולח, למשל `whatsapp:+14155238886` |
| `ALLOWED_WA_ID` | ✅ | המספר היחיד המורשה, למשל `whatsapp:+9725XXXXXXXX` |
| `PUBLIC_URL` | ➖ | כתובת ציבורית לאימות חתימת Twilio (מומלץ מאוד) |
| `OPENROUTER_KEY` | ✅ | מפתח OpenRouter |
| `REDIS_URL` | ➖ | Upstash `redis://` לזיכרון מתמשך |
| `APP_MODULE` | ➖ | בחירת מתאם: `twilio_bot:app` (ברירת מחדל) / `wa_bot:app` |

---

## נספח A — Meta Cloud API

מתאם חלופי (`wa_bot.py`) עבור מי שכן רוצה להשתמש ב-WhatsApp Cloud API הרשמי של
Meta. **דורש חשבון Meta/Facebook Business.** הגדר `APP_MODULE=wa_bot:app`.

1. **אפליקציה:** <https://developers.facebook.com/apps> → Create App (Business)
   → Add Product → WhatsApp.
2. **פרטים** (WhatsApp → API Setup): `WA_PHONE_ID` (Phone number ID),
   והוסף את המספר שלך כ-recipient. המספר (`9725XXXXXXXX`) הוא `ALLOWED_WA_ID`.
3. **App Secret:** App settings → Basic → `WA_APP_SECRET`.
4. **טוקן קבוע (חובה):** הטוקן הזמני תקף 24 שעות. צור **System User token** ב-
   <https://business.facebook.com/settings> עם ההרשאות `whatsapp_business_messaging`
   ו-`whatsapp_business_management` → `WA_TOKEN`.
5. **Verify token:** מחרוזת שאתה ממציא → `WA_VERIFY_TOKEN`.
6. **Webhook** (WhatsApp → Configuration): Callback `https://<host>/webhook`,
   Verify token כנ"ל, ואז **Subscribe** לשדה `messages`.

הרצה: `uvicorn wa_bot:app ...`. מתאם זה מוסיף חיווי "מקליד..." ווי כחול.

---

## נספח B — הרצה מקומית עם Baileys (ללא פייסבוק, ללא Twilio)

מריצים הכל **על המחשב שלך** ומחברים את הבוט למספר WhatsApp דרך "מכשירים
מקושרים" (QR), בדיוק כמו WhatsApp Web — אבל דרך הפרוטוקול, לא דרך דפדפן.

```
WhatsApp ⇄ baileys/index.js (Node) ⇄ local_server.py (core) ⇄ OpenRouter
```

> ⚠️ **סיכון חסימה:** חיבור לא-רשמי נוגד את ה-ToS של WhatsApp. השתמש ב**מספר
> ייעודי נפרד** (SIM/eSIM זול), לא במספר האישי — כך חסימה לא פוגעת בוואטסאפ שלך.
> בידוד המכונה לא מגן על המספר; רק מספר נפרד מגן.

### הרצה

צריך **שני תהליכים** (שני טרמינלים). התקן Python (שלב 3) ו-Node 18+.

**טרמינל 1 — שירות הליבה (Python):**
```bash
export OPENROUTER_KEY=...        # ו-REDIS_URL אם רוצים זיכרון מתמשך
export LOCAL_TOKEN=some-secret   # אופציונלי, אבל מומלץ
uvicorn local_server:app --host 127.0.0.1 --port 8090
```

**טרמינל 2 — גשר Baileys (Node):**
```bash
cd baileys
npm install
export ALLOWED_WA_ID=972501234567   # המספר הייעודי, ספרות בלבד
export LOCAL_TOKEN=some-secret       # זהה לזה שבטרמינל 1
node index.js
```

בהרצה הראשונה יודפס **QR** — פתח WhatsApp במספר הייעודי → **מכשירים מקושרים →
קשר מכשיר** → סרוק. מהרגע הזה, כל הודעה מהמספר המורשה מקבלת תשובה. הסשן נשמר
בתיקייה `baileys/auth/` (לא נכנס ל-git), כך שאין צורך לסרוק שוב בכל הפעלה.

### מה עובד כאן
כל היכולות מ[סעיף 6](#6-שימוש-ופקודות) — פקודות, מודלים, fallback, קריאת
תמונות, זיכרון — **בנוסף** ל"מקליד..." ווי כחול (Baileys תומך ב-presence,
בשונה מ-Twilio). אין צורך ב-`PUBLIC_URL` — הכל מקומי.

---

## רישיון

[MIT](LICENSE) © 2026 Eliezer Avihail
