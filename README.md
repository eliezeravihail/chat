# chat — עוזר WhatsApp חכם בעברית

בוט WhatsApp אישי המחובר למודלי שפה (חינמיים, או Claude / GPT). שיחה טבעית
בעברית, זיכרון שיחה, ושאלות על תמונות. מבוסס **Twilio** — בלי חשבון פייסבוק,
בלי סיכון חסימת מספר, ובלי פעלולים.

```
WhatsApp ⇄ Twilio ⇄ הבוט (FastAPI) ⇄ מודל שפה (OpenRouter)
```

דרכים להריץ: [הכי פשוט (בלי שרת)](#הכי-פשוט--בלי-ngrok-ובלי-שרת), [מקומי](#דרך-1--מקומי),
או [בענן (תמיד פעיל)](#דרך-2--בענן-תמיד-פעיל).

---

## לפני שמתחילים (משותף לשתי הדרכים)

1. **מפתח OpenRouter** (חינם): <https://openrouter.ai/keys> → **Create Key**.
2. **חשבון Twilio** (חינם): <https://www.twilio.com/try-twilio>. אין צורך בפייסבוק.
3. **הפעל WhatsApp Sandbox:** ב-Console → **Messaging → Try it out → Send a
   WhatsApp message**. תקבל:
   - **מספר sandbox** (בד"כ ‎+1 415 523 8886‎) → זה `TWILIO_FROM`.
   - **קוד הצטרפות** בסגנון `join <מילה>`.
   שלח `join <מילה>` מה-WhatsApp **הרגיל** שלך אל מספר ה-sandbox. זהו — המספר
   שלך מחובר, בשיחה פרטית 1-על-1 (לא מתערבב עם אף אחד).
4. מהעמוד הראשי ב-Console: **Account SID** ו-**Auth Token**.

השדות שתמלא (ב-`.env` מקומית או ב-secrets בענן):
```bash
OPENROUTER_KEY=sk-or-...
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM=whatsapp:+14155238886
ALLOWED_WA_ID=whatsapp:+972500000000    # המספר שלך (שממנו תכתוב)
PUBLIC_URL=...                           # ממולא בשלב הרלוונטי למטה
```

> ה-`ALLOWED_WA_ID` הוא ההגנה שלך: הבוט עונה **רק** למספר הזה, מתעלם מכל אחד אחר.

---

## הכי פשוט — בלי ngrok ובלי שרת

אם אתה רק רוצה שזה יעבוד עם מינימום צעדים: הסקריפט `twilio_poll.py` **שואל** את
Twilio כל כמה שניות אם הגיעה הודעה — אז **אין צורך ב-ngrok, ב-webhook, או בכתובת
ציבורית.** אחרי שמילאת את `.env` (בלי `PUBLIC_URL`):

```bash
python -m pip install -r requirements.txt
python twilio_poll.py
```

זהו — כתוב לבוט מהוואטסאפ שלך וקבל תשובה. **לא צריך להגדיר webhook ב-Twilio.**
חסרון יחיד: תגובה איטית ב-2–4 שניות. (רוצה תגובה מיידית או ריצה בענן 24/7? המשך לדרך 1/2.)

---

## דרך 1 — מקומי

תגובה מיידית (webhook). צריך **Python 3.11+** ו-[ngrok](https://ngrok.com) (חינם).

**התקנה** (פעם אחת):

```bash
git clone https://github.com/eliezeravihail/chat.git
cd chat
python -m venv .venv
```

הפעל את ה-venv — **לפי מערכת ההפעלה:**
- **Windows (cmd):** `.venv\Scripts\activate`
- **macOS / Linux:** `source .venv/bin/activate`

ואז:
```bash
pip install -r requirements.txt
copy .env.example .env       # Windows.  ב-mac/linux: cp .env.example .env
```
מלא את השדות ב-`.env` (בינתיים בלי `PUBLIC_URL`). הבוט טוען את `.env` **לבד** —
אין צורך ב-`source`.

**הרצה** — שני טרמינלים (בשניהם הפעל קודם את ה-venv):
```bash
# טרמינל 1 — הבוט
python -m uvicorn twilio_bot:app --host 0.0.0.0 --port 8080

# טרמינל 2 — מנהרה ציבורית
ngrok http 8080              # העתק את כתובת ה-https שמופיעה
```

1. עדכן ב-`.env`: `PUBLIC_URL=https://xxxx.ngrok-free.app`, וסגור+הפעל מחדש את טרמינל 1.
2. ב-**Twilio Console → Sandbox settings → "When a message comes in"** הדבק:
   `https://xxxx.ngrok-free.app/webhook` (method **POST**).
3. שלח הודעה מה-WhatsApp שלך למספר ה-sandbox → תקבל תשובה. 🎉

(הבוט חי כל עוד שני הטרמינלים פתוחים. כתובת ngrok החינמית מתחלפת בכל הרצה.)

---

## דרך 2 — בענן (תמיד פעיל)

Fly.io — **HTTPS אוטומטי** (אין צורך ב-ngrok), רץ 24/7. ה-`Dockerfile` מוכן.

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
fly launch --no-deploy         # בחר שם, למשל my-wa-bot

fly secrets set \
  OPENROUTER_KEY=sk-or-... \
  TWILIO_ACCOUNT_SID=AC... \
  TWILIO_AUTH_TOKEN=... \
  TWILIO_FROM="whatsapp:+14155238886" \
  ALLOWED_WA_ID="whatsapp:+972500000000" \
  PUBLIC_URL="https://my-wa-bot.fly.dev"

fly deploy
```

1. ב-**Twilio Console → Sandbox settings → "When a message comes in"** הדבק:
   `https://my-wa-bot.fly.dev/webhook` (method **POST**).
2. שלח הודעה → תשובה. רץ תמיד, גם כשהמחשב כבוי.

> עלות זעירה עד אפסית לשימוש כזה. חלופות: **Render** (חינם, אבל נרדם בחוסר
> פעילות) או VM ב-**GCP**.

---

## פקודות (בתוך הצ'אט)

| פקודה | פעולה |
| --- | --- |
| `/model <שם>` | החלפת מודל: `claude`, `gpt`, `gemini`, `deepseek`, `llama`, `qwen` |
| `/models` | רשימת המודלים והנוכחי |
| `/clear` | ניקוי הזיכרון |

ברירת המחדל היא מודל **חינמי**. `/model claude` דורש קרדיט ב-OpenRouter.
שליחת **תמונה** → הבוט מנתח אותה.

---

## הערות

- **זיכרון מתמשך:** בברירת מחדל הזיכרון נמחק ב-redeploy. לזיכרון של 30 יום חבר
  Redis חינם מ-<https://upstash.com>: `fly secrets set REDIS_URL="rediss://..."`.
- **Sandbox:** זו סביבת הבדיקה של Twilio (הגבלת קצב קלה; אתה תמיד יוזם, אז זה
  מספיק לשימוש אישי). למספר WhatsApp ייעודי משלך צריך Sender בתשלום ב-Twilio
  (שכרוך בחשבון Meta Business — לכן ה-sandbox עדיף כאן).

<sub>הקוד כולל גם מתאם **Baileys** מקומי (מספר משלך דרך QR, בלי ספק חיצוני) ומתאם
**Meta Cloud API** רשמי — ראה `baileys/` ו-`wa_bot.py`. לא נדרשים לשתי הדרכים למעלה.</sub>

## רישיון

[MIT](LICENSE) © 2026 Eliezer Avihail
