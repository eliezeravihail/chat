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

## 🚀 התחלה מהירה — הרצה מקומית (Baileys)

הדרך הפשוטה ביותר, ללא פייסבוק וללא ספק חיצוני. הכל רץ **על המחשב שלך**.

### מה צריך להכין (פעם אחת)

1. **Python 3.11+** ו-**Node.js 18+** מותקנים. בדיקה:
   ```bash
   python3 --version    # ≥ 3.11
   node --version       # ≥ 18
   ```
   אם חסר: Python מ-<https://python.org>, Node מ-<https://nodejs.org>.

2. **מפתח OpenRouter** (חינם): היכנס ל-<https://openrouter.ai/keys> → **Create Key** → העתק.

3. **מספר WhatsApp ייעודי** — ‼️ **לא המספר האישי שלך.** קנה SIM/eSIM זול או
   השתמש במספר שני. רשום עליו WhatsApp רגיל בטלפון. זה המספר שהבוט יתחבר אליו,
   ואם ייחסם — לא איבדת כלום. רשום את המספר בפורמט בינלאומי ללא `+`, למשל
   `972501234567`.

### הורדה והגדרה

```bash
# 1. הורד את הקוד
git clone https://github.com/eliezeravihail/chat.git
cd chat

# 2. התקן את התלויות של הליבה (Python)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. צור קובץ הגדרות ומלא אותו
cp .env.example .env
```

פתח את `.env` בעורך ומלא **רק** את שלוש השורות האלה (השאר אפשר להשאיר ריק):
```bash
OPENROUTER_KEY=sk-or-...         # המפתח מ-OpenRouter
ALLOWED_WA_ID=972501234567       # המספר הייעודי, ספרות בלבד
LOCAL_TOKEN=בחר-סיסמה-כלשהי       # מגן על השירות המקומי
```

### הרצה (פקודה אחת)

```bash
./run-local.sh
```

הסקריפט מפעיל את שירות הליבה ואת גשר ה-Baileys יחד. **בהרצה הראשונה יופיע QR
בטרמינל** — בטלפון עם המספר הייעודי: **WhatsApp → הגדרות → מכשירים מקושרים →
קשר מכשיר → סרוק את ה-QR**.

מהרגע הזה — שלח הודעה מהמספר הייעודי לעצמו (או ממנו לכל מספר שרשום כ-`ALLOWED_WA_ID`)
ותקבל תשובה מהמודל. 🎉 ההתחברות נשמרת, אז בפעמים הבאות אין צורך לסרוק שוב.

> **Windows:** אם `./run-local.sh` לא רץ, השתמש ב-Git Bash / WSL, או הרץ ידנית
> את שני התהליכים לפי [נספח B](#נספח-b--הרצה-מקומית-עם-baileys-ללא-פייסבוק-ללא-twilio).

### שיישאר פועל תמיד

הבוט חי כל עוד הטרמינל פתוח. אפשרויות להשאיר אותו רץ:
- **הכי פשוט:** השאר את המחשב והטרמינל פתוחים.
- **מסודר יותר:** הרץ בתוך `tmux` או `screen` כדי שיישרד סגירת טרמינל.
- **תמיד-זמין בענן (חינם):** הרץ על VM חינמי — ראה
  [נספח C](#נספח-c--הרצה-בענן-בחינם-google-cloud-e2-micro) למדריך מלא ל-Google
  Cloud e2-micro, כולל איך להגיע לסריקה כשזה בענן. **חשוב:** ענן מבודד את המחשב,
  לא את המספר — סיכון החסימה תלוי במספר, ולכן המספר הייעודי חשוב בכל מקרה.
- **בלי טלפון פיזי?** אפשר לרשום WhatsApp על מספר וירטואלי דרך אמולטור —
  ראה [נספח D](#נספח-d--whatsapp-בלי-טלפון-פיזי-מספר-וירטואלי).

זהו — כל השאר במסמך הוא לחלופות (Twilio בענן, Meta הרשמי) ולפרטים מתקדמים.

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

> **הערה על מדיניות Meta (מעודכן יוני 2026):** באוקטובר 2025 מטא אסרה על עוזרי
> AI כלליים ב-WhatsApp Business API (זו הסיבה ש-1-800-ChatGPT נסגר בינואר 2026).
> ב-9.6.2026 הוציאה הנציבות האירופית **צו ביניים** (IP/26/1276) המחייב את מטא
> להחזיר גישה חינמית לעוזרי AI מתחרים ב-API הרשמי, בתנאים שלפני אוקטובר 2025 —
> כך שאיסור ה-AI על ה-API הרשמי מושעה בפועל. **שלוש הסתייגויות:** (1) הצו תקף
> ב-EEA בלבד; (2) הוא אינו מבטל את הצורך בחשבון Meta/Business ל-API הרשמי;
> (3) הוא אינו הופך חיבורים לא-רשמיים (Baileys/WhatsApp Web) לחוקיים — שם עדיין
> יש סיכון חסימת מספר, ולכן מומלץ מספר ייעודי נפרד (נספח B). מטא הודיעה שתערער.

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

## נספח C — הרצה בענן בחינם (Google Cloud e2-micro)

אותו סטאפ של נספח B, אבל על **VM חינמי שרץ 24/7** במקום המחשב שלך.

### למה דווקא Google e2-micro
בין הטיירים החינמיים "לתמיד" (נכון ל-2026): AWS ו-Azure כבר לא מציעים VM חינמי
לתמיד (רק קרדיט זמני). Oracle נדיב יותר בחומרה, אבל **מכבה מכונות בטלות** (ניצול
CPU < 20% ל-7 ימים) — והבוט שלנו כמעט תמיד בטל, בדיוק הפרופיל בסיכון. ל-Google
e2-micro **אין כיבוי-בטלה**, ולכן הוא האמין ביותר לבוט הזה (1GB RAM — יותר ממספיק).

> Oracle עדיין אפשרי אם רוצים יותר RAM — רק צריך cron שמייצר עומס CPU קל כדי
> להימנע מהכיבוי. לבוט אישי, Google פשוט יותר.

### 1. יצירת ה-VM
1. היכנס ל-<https://console.cloud.google.com> (דורש כרטיס אשראי לאימות; יש גם
   $300 קרדיט ל-90 יום, אבל ה-e2-micro חינמי לתמיד גם אחריו).
2. **Compute Engine → VM instances → Create instance**.
3. הגדרות: **Region** אחד מ-`us-west1` / `us-central1` / `us-east1` (רק אלה
   חינמיים), **Machine type: `e2-micro`**, **Boot disk: Ubuntu 24.04 LTS**,
   גודל דיסק 30GB (סטנדרטי — כלול בחינם).
4. **Create**.

### 2. התחברות ל-VM
בעמוד ה-VM לחץ על כפתור **SSH** — נפתח טרמינל בדפדפן, ישירות אל השרת. אין צורך
בהגדרת מפתחות. כל מה שתריץ מכאן רץ בענן.

### 3. התקנה
בטרמינל של ה-VM:
```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip curl
# Node 20:
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

git clone https://github.com/eliezeravihail/chat.git
cd chat
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env      # מלא OPENROUTER_KEY, ALLOWED_WA_ID, LOCAL_TOKEN, ו-PAIR_NUMBER
```

### 4. איך מגיעים לסריקה כשזה בענן — שתי דרכים

**דרך א' — QR ב-SSH (עם טלפון):**
פשוט הרץ `./run-local.sh`. ה-QR מצויר כ-ASCII **בתוך חלון ה-SSH** — כוון את
מצלמת הטלפון אל המסך וסרוק (WhatsApp → מכשירים מקושרים → קשר מכשיר).

**דרך ב' — קוד צימוד (בלי מצלמה, מומלץ בענן):**
אם הגדרת `PAIR_NUMBER` (מספר הבוט) ב-`.env`, במקום QR יודפס **קוד בן 8 תווים**:
```
🔑 קוד צימוד: ABCD-1234
```
ב-WhatsApp של הבוט: **קשר מכשיר → "קשר עם מספר טלפון במקום" → הזן את הקוד**.
אין צורך במצלמה — מושלם לשרת מרוחק.

### 5. שיישאר רץ אחרי שתסגור את ה-SSH
הרץ בתוך `tmux` כדי שהתהליך ישרוד ניתוק:
```bash
sudo apt install -y tmux
tmux new -s bot
./run-local.sh          # סרוק/הזן קוד
# נתק מ-tmux בלי לעצור: Ctrl-b ואז d
```
לחזרה: `tmux attach -t bot`. (לפתרון "מקצועי" יותר אפשר systemd service —
בקש ואוסיף.)

---

## נספח D — WhatsApp בלי טלפון פיזי (מספר וירטואלי)

Baileys מתחבר כ**מכשיר מקושר** לחשבון WhatsApp קיים — כלומר צריך שהמספר יהיה
**רשום** ב-WhatsApp במקום כלשהו. בלי טלפון פיזי, "המקום הזה" הוא אמולטור אנדרואיד
על המחשב.

### שלבים
1. **מספר וירטואלי שמקבל SMS/שיחה** לצורך ה-OTP. ⚠️ הרבה שירותי SMS-חינם חסומים
   ע"י WhatsApp; אמין יותר eSMS/eSIM זול בתשלום או שירות מספרים וירטואליים ייעודי.
2. **אמולטור אנדרואיד** על המחשב: Genymotion / BlueStacks / Android Studio (AVD),
   או Waydroid בלינוקס. התקן בו את אפליקציית **WhatsApp**.
3. **רישום:** פתח WhatsApp באמולטור, הזן את המספר הווירטואלי, וקבל את קוד ה-OTP
   דרך שירות המספר. עכשיו יש לך חשבון WhatsApp פעיל — בלי טלפון פיזי.
4. **קישור הבוט בלי מצלמה:** הרץ את הגשר עם `PAIR_NUMBER` (שלב 4ב' בנספח C), ובאמולטור:
   **קשר מכשיר → "קשר עם מספר טלפון במקום" → הזן את הקוד**. הצימוד טקסטואלי לגמרי,
   בלי לצלם QR — מה שפותר את הבעיה של "מסך מול מצלמה".

### חשוב לדעת
- **חשבון "ראשי" צריך להישאר קיים.** ב-WhatsApp Multi-Device המכשיר הראשי (האמולטור)
  לא חייב להיות מחובר כל הזמן, אבל **חייב לעלות לרשת לפחות פעם ב-~14 יום**, אחרת
  המכשירים המקושרים מתנתקים. שמור את האמולטור ופתח אותו מדי פעם.
- זה עדיין חיבור לא-רשמי → **סיכון חסימה קיים.** לכן המספר הווירטואלי הייעודי הוא
  גם ההגנה שלך: אם ייחסם, לא איבדת דבר.

---

## רישיון

[MIT](LICENSE) © 2026 Eliezer Avihail
