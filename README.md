# chat — עוזר WhatsApp חכם בעברית

בוט WhatsApp אישי שמחובר למודלי שפה (חינמיים, או Claude / GPT). שיחה טבעית
בעברית, זיכרון שיחה, ושאלות על תמונות.

```
WhatsApp ⇄ הבוט (Node + Python) ⇄ מודל שפה (OpenRouter)
```

יש **שתי דרכים להריץ**. בחר אחת: [מקומי](#דרך-1--מקומי) או [בענן](#דרך-2--בענן-חינם-24-7).

---

## לפני שמתחילים (משותף לשתי הדרכים)

1. **מפתח OpenRouter** (חינם): <https://openrouter.ai/keys> → **Create Key**.
2. **שני מספרי WhatsApp שונים:**
   - **המספר שלך** — היומיומי, שממנו תכתוב לבוט.
   - **מספר ייעודי לבוט** — שהבוט מתחבר אליו. **לא האישי!** ראה [מספר לבוט](#מספר-לבוט).

---

## דרך 1 — מקומי

רץ על המחשב שלך. צריך **Python 3.11+** ו-**Node 18+**.

```bash
git clone https://github.com/eliezeravihail/chat.git
cd chat
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

פתח את `.env` ומלא **4 שורות** (השאר ריק):

```bash
OPENROUTER_KEY=sk-or-...      # המפתח מ-OpenRouter
ALLOWED_WA_ID=972500000000    # המספר שלך (שכותב לבוט)
PAIR_NUMBER=972511111111      # מספר הבוט (הייעודי)
LOCAL_TOKEN=בחר-סיסמה-כלשהי
```

הרץ:

```bash
./run-local.sh
```

בהרצה הראשונה יודפס **קוד צימוד בן 8 תווים**. בטלפון עם **מספר הבוט**:
**WhatsApp → מכשירים מקושרים → קשר מכשיר → "קשר עם מספר טלפון במקום" → הזן את הקוד.**

זהו — שלח הודעה מהמספר שלך אל מספר הבוט, ותקבל תשובה. 🎉
הבוט חי כל עוד הטרמינל פתוח.

---

## דרך 2 — בענן (חינם, 24/7)

רץ על VM חינמי ב-Google Cloud, תמיד פעיל — גם כשהמחשב שלך כבוי.

1. היכנס ל-<https://console.cloud.google.com> → **Compute Engine → Create instance**
   (דורש כרטיס אשראי לאימות; ה-e2-micro חינמי לתמיד).
2. בחר: **Region** `us-central1`, **Machine type** `e2-micro`, **Boot disk** Ubuntu 24.04 → **Create**.
3. לחץ על כפתור **SSH** (נפתח טרמינל בדפדפן, על השרת). הרץ בו:

```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip curl tmux
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs
git clone https://github.com/eliezeravihail/chat.git && cd chat
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env && nano .env        # מלא את אותן 4 שורות כמו בדרך 1
tmux new -s bot
./run-local.sh                            # יודפס קוד צימוד — קשר כמו בדרך 1
```

4. כדי שהבוט ימשיך לרוץ אחרי שתסגור: נתק מ-`tmux` עם **Ctrl-b** ואז **d**.
   לחזרה מאוחר יותר: `tmux attach -t bot`.

> **למה Google?** Oracle מכבה מכונות בטלות (הבוט שלנו בטל רוב הזמן), ו-AWS/Azure
> כבר לא מציעים VM חינמי לתמיד. e2-micro חינמי לתמיד ולא נכבה.

---

## פקודות (בתוך הצ'אט)

| פקודה | פעולה |
| --- | --- |
| `/model <שם>` | החלפת מודל: `claude`, `gpt`, `gemini`, `deepseek`, `llama`, `qwen` |
| `/models` | רשימת המודלים והנוכחי |
| `/clear` | ניקוי הזיכרון |

ברירת המחדל היא מודל **חינמי**. `/model claude` דורש קרדיט ב-OpenRouter.
שליחת **תמונה** → הבוט מנתח אותה. הזיכרון נשמר 30 יום (עם Redis; אחרת עד restart).

---

## מספר לבוט

הבוט מתחבר ל-WhatsApp דרך **מספר ייעודי — לא האישי שלך.** חיבור לא-רשמי עלול
לגרום לחסימת המספר לצמיתות; אם זה מספר זניח, לא הפסדת דבר.

איך להשיג מספר:

- **SIM / eSIM זול** — הכי אמין ופשוט.
- **מספר "כשר" או קו נייח (בלי SMS)** — עובד! בזמן הרישום ב-WhatsApp בחר
  **"התקשרו אליי"**, והקוד יוקרא ב**שיחה קולית**. המספר צריך רק לקבל שיחה אחת —
  הוא לא מריץ WhatsApp ולא צריך אינטרנט.
- **Twilio?** אפשר לקנות מספר (~$1/חודש) שמקבל SMS ולקרוא את הקוד בקונסולה של
  Twilio — **אבל** WhatsApp חוסם לעיתים קרובות מספרי VoIP בעת הרישום. לא אמין;
  העדף SIM זול או מספר כשר.

**בלי טלפון פיזי?** התקן WhatsApp באמולטור אנדרואיד (BlueStacks / Genymotion /
Waydroid), רשום בו את המספר הייעודי (אימות קולי כנ"ל), וקשר את הבוט בקוד הצימוד.
הערה: המכשיר שנרשם צריך לעלות לרשת פעם ב-~14 יום, אחרת הקישור מתנתק.

---

<sub>הערה למפתחים: הקוד כולל גם מתאמים רשמיים ל-Twilio ול-Meta Cloud API
(`twilio_bot.py`, `wa_bot.py`) — לא נדרשים לשתי הדרכים שלמעלה.</sub>

## רישיון

[MIT](LICENSE) © 2026 Eliezer Avihail
