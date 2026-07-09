# chat — גשר WhatsApp ⇄ OpenRouter

בוט שמחבר את **WhatsApp** (דרך Meta Cloud API הרשמי) אל **OpenRouter**, וכך
מאפשר לשוחח עם מודלי שפה (Claude / GPT / Gemini / מודלים חינמיים) ישירות מתוך
צ'אט בוואטסאפ. הבוט נעול ל**משתמש מורשה יחיד** ועלות ההפעלה חינם או קרוב לכך.

```
WhatsApp → Meta Cloud API → Webhook (FastAPI) → OpenRouter → תשובה חזרה
```

---

## תוכן עניינים

1. [מה צריך לפני שמתחילים](#1-מה-צריך-לפני-שמתחילים)
2. [OpenRouter — מפתח API](#2-openrouter--מפתח-api)
3. [Meta / WhatsApp — הקמת האפליקציה](#3-meta--whatsapp--הקמת-האפליקציה)
4. [הרצה מקומית (לפיתוח)](#4-הרצה-מקומית-לפיתוח)
5. [פריסה לענן (Fly.io)](#5-פריסה-לענן-flyio)
6. [חיבור ה-webhook ב-Meta](#6-חיבור-ה-webhook-ב-meta)
7. [שימוש ופקודות](#7-שימוש-ופקודות)
8. [פתרון תקלות](#8-פתרון-תקלות)
9. [רשימת משתני סביבה](#9-רשימת-משתני-סביבה)

---

## 1. מה צריך לפני שמתחילים

- חשבון **Meta / Facebook** (רגיל — ישמש ליצירת Meta Business).
- מספר טלפון שאפשר לקבל אליו הודעת WhatsApp לצורך בדיקה (ה-**wa_id** שלך).
- חשבון **OpenRouter** (חינם).
- Python 3.11+ להרצה מקומית, או חשבון **Fly.io** (חינם) לפריסה.

> **הערה על אבטחה:** אם החסימה לרשת הותקנה על ידי מעסיק או גורם שאתה כפוף לו —
> ודא שבניית ערוץ עוקף מקובלת עליהם. אם זו החלטה שלך על המכשיר שלך, אין בעיה.

---

## 2. OpenRouter — מפתח API

1. היכנס ל-<https://openrouter.ai> והתחבר.
2. גש ל-<https://openrouter.ai/keys> → **Create Key**.
3. העתק את המפתח — זה הערך של `OPENROUTER_KEY`.

מודלים עם סיומת `:free` (DeepSeek, Llama, Qwen, Gemini Flash) הם ללא עלות. כדי
להשתמש ב-Claude / GPT צריך להטעין קרדיט קטן בחשבון OpenRouter.

---

## 3. Meta / WhatsApp — הקמת האפליקציה

### 3.1 יצירת אפליקציה
1. גש ל-<https://developers.facebook.com/apps> → **Create App**.
2. בחר סוג **Business**.
3. באפליקציה שנוצרה: **Add Product → WhatsApp → Set up**.

### 3.2 השגת הפרטים
בתוך **WhatsApp → API Setup** תמצא:
- **Phone number ID** → הערך של `WA_PHONE_ID` (זה מזהה, *לא* מספר הטלפון).
- **Temporary access token** → לשימוש זמני בלבד (ראה 3.4).
- שדה להוספת **recipient phone number** — הוסף את המספר שלך ואשר את קוד ה-OTP.
  המספר הזה, בפורמט בינלאומי ללא `+` (למשל `9725XXXXXXXX`), הוא `ALLOWED_WA_ID`.

### 3.3 App Secret
**App settings → Basic → App Secret → Show** → הערך של `WA_APP_SECRET`.

### 3.4 טוקן קבוע (חובה!)
הטוקן הזמני תקף **24 שעות בלבד** — בלעדיו הבוט מת למחרת. יש ליצור **System User token**:

1. <https://business.facebook.com/settings> → **Users → System Users → Add**.
2. צור system user (תפקיד Admin).
3. **Add Assets** → בחר את האפליקציה → הרשאות מלאות.
4. **Generate New Token** → בחר את האפליקציה → סמן `whatsapp_business_messaging`
   ו-`whatsapp_business_management` → **Generate**.
5. העתק את הטוקן — זה הערך של `WA_TOKEN` (שמור אותו, הוא לא יוצג שוב).

### 3.5 Verify Token
`WA_VERIFY_TOKEN` הוא מחרוזת שאתה ממציא (למשל `my-secret-verify-123`). היא צריכה
להיות זהה כאן ובממשק ה-webhook של Meta (שלב 6).

---

## 4. הרצה מקומית (לפיתוח)

```bash
# 1. שכפול והתקנה
git clone https://github.com/eliezeravihail/chat.git
cd chat
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. הגדרת משתני סביבה
cp .env.example .env      # פתח וערוך את הערכים
set -a; source .env; set +a

# 3. הרצה
uvicorn wa_bot:app --host 0.0.0.0 --port 8080
```

בדוק שהשרת חי:
```bash
curl http://localhost:8080/health      # → {"status":"ok"}
```

כדי ש-Meta תוכל להגיע ל-webhook המקומי, חשוף אותו לאינטרנט עם tunnel:
```bash
ngrok http 8080
```
העתק את כתובת ה-`https://...` שקיבלת — תשתמש בה בשלב 6 כ-`https://<ngrok>/webhook`.

---

## 5. פריסה לענן (Fly.io)

הפרויקט כולל `Dockerfile` ו-`fly.toml` מוכנים.

```bash
# התקנת ה-CLI והתחברות
curl -L https://fly.io/install.sh | sh
fly auth login

# יצירת האפליקציה (בחר שם ייחודי; ערוך את app ב-fly.toml בהתאם)
fly launch --no-deploy

# הזרקת הסודות
fly secrets set \
  WA_TOKEN=... \
  WA_PHONE_ID=... \
  WA_VERIFY_TOKEN=... \
  WA_APP_SECRET=... \
  ALLOWED_WA_ID=... \
  OPENROUTER_KEY=...

# פריסה
fly deploy
```

כתובת ה-webhook שלך תהיה `https://<app-name>.fly.dev/webhook`.

> אלטרנטיבה: המאגר כולל גם `Procfile`, כך שאפשר לפרוס ב-**Render** או **Railway**
> בלי שינויים — פשוט הגדר שם את אותם משתני הסביבה.

---

## 6. חיבור ה-webhook ב-Meta

ב-**Meta app → WhatsApp → Configuration → Webhook → Edit**:

| שדה | ערך |
| --- | --- |
| **Callback URL** | `https://<host>/webhook` (Fly.io או ngrok) |
| **Verify token** | הערך של `WA_VERIFY_TOKEN` |

לחץ **Verify and Save** — Meta תשלח `GET /webhook`, והשרת יחזיר את ה-challenge.
לאחר מכן, תחת **Webhook fields**, לחץ **Subscribe** על השדה **`messages`**.

---

## 7. שימוש ופקודות

שלח הודעת WhatsApp למספר הבוט מהמספר המורשה — תקבל תשובה מהמודל.

| פקודה | פעולה |
| --- | --- |
| `/models` | רשימת המודלים הזמינים והמודל הנוכחי |
| `/model <שם>` | החלפת מודל (מאפס את ההקשר) |
| `/model` | הצגת המודל הנוכחי |
| `/clear` | ניקוי היסטוריית השיחה |

**Aliases:** `claude`, `gpt`, `gemini`, `deepseek`, `llama`, `qwen`. אפשר גם להעביר
מזהה OpenRouter מלא, למשל `/model anthropic/claude-sonnet-4.5`.

---

## 8. פתרון תקלות

| תסמין | סיבה סבירה | פתרון |
| --- | --- | --- |
| ה-webhook לא עובר verify | verify token לא תואם | ודא ש-`WA_VERIFY_TOKEN` זהה בקוד ובממשק Meta |
| `403 bad signature` בלוגים | `WA_APP_SECRET` שגוי | העתק מחדש מ-App settings → Basic |
| אין תשובה בכלל | המספר לא ב-whitelist | ודא ש-`ALLOWED_WA_ID` שווה בדיוק ל-wa_id ששולח (ללא `+`) |
| תשובות כפולות | קריאת LLM חוסמת את ה-webhook | הקוד כבר מחזיר `200` מיד ומריץ ברקע — ודא שאתה על הגרסה הזו |
| הבוט מת אחרי יום | נעשה שימוש בטוקן הזמני | החלף ל-System User token (שלב 3.4) |
| `⚠️ שגיאת מודל` על אורך | context window של מודל חינמי קטן | הורד את `HISTORY_TURNS` ב-`wa_bot.py` |
| היסטוריה נמחקת ב-restart | מצב in-memory | חבר `REDIS_URL` (Upstash) — ראה ההערה בקוד |

---

## 9. רשימת משתני סביבה

ראה `.env.example`. סיכום:

| משתנה | חובה | תיאור |
| --- | :---: | --- |
| `WA_TOKEN` | ✅ | System User access token קבוע |
| `WA_PHONE_ID` | ✅ | Phone number ID מ-Meta (מזהה, לא מספר) |
| `WA_VERIFY_TOKEN` | ✅ | מחרוזת שרירותית, זהה למה שמוזן ב-Meta |
| `WA_APP_SECRET` | ✅ | App secret, לאימות `X-Hub-Signature-256` |
| `ALLOWED_WA_ID` | ✅ | ה-wa_id היחיד המורשה, למשל `9725XXXXXXXX` |
| `OPENROUTER_KEY` | ✅ | מפתח OpenRouter |
| `REDIS_URL` | ➖ | Upstash `redis://` (אופציונלי; נופל חזרה לזיכרון) |

---

## רישיון

[MIT](LICENSE) © 2026 Eliezer Avihail
