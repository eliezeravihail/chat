# chat — בוט WhatsApp חכם בעברית

בוט שמחבר WhatsApp למודלי שפה (HY3 / Claude / GPT / חינמיים): שיחה טבעית
בעברית, זיכרון שיחה, ושאלות על תמונות. הגישה מוגבלת למספרים מורשים בלבד.

יש **שתי גרסאות** — בוחרים אחת:

| גרסה | יתרון | חיסרון | מדריך |
| --- | --- | --- | --- |
| **1 · Twilio** | הכי פשוט, רשמי, בלי סיכון חסימה | מגבלת **50 הודעות/יום** (sandbox) | כאן למטה ⬇️ |
| **2 · Hermes** | **בלי מגבלת הודעות**, סוכן מלא | דורש מספר WhatsApp ייעודי + טלפון ישן | [HERMES.md](HERMES.md) |

שתי הגרסאות יכולות לרוץ על אותו **VM חינמי** (למשל Google Cloud e2-micro
או Oracle Cloud Always Free).

---

## מבנה המאגר — מה כל קובץ

| קובץ | תפקיד | שייך ל |
| --- | --- | --- |
| `core.py` | המוח: מודלים, זיכרון, פקודות, עברית | Twilio |
| `twilio_poll.py` | הבוט — מושך הודעות מ-Twilio ועונה | Twilio |
| `monitor-twilio.py` | בדיקת מצב Twilio → התראת ntfy (אופציונלי) | Twilio |
| `setup-twilio-vm.sh` | הקמת ה-VM בפקודה אחת | Twilio |
| `.github/workflows/deploy-gcp.yml` | פריסה אוטומטית (ראה [למטה](#מה-ה-github-action-עושה)) | Twilio |
| `.env.example` | דוגמת הגדרות (להרצה מקומית) | Twilio |
| `requirements.txt` | תלויות Python | Twilio |
| `hermes/setup-hermes-vm.sh` | הקמת Hermes בפקודה אחת | Hermes |
| `HERMES.md` | המדריך המלא ל-Hermes | Hermes |

---

# גרסה 1 — Twilio

**מה זה:** בוט (`twilio_poll.py`) שמדבר עם WhatsApp דרך ה-sandbox של Twilio,
ועם המודלים דרך OpenRouter. לא צריך webhook ציבורי — הבוט מושך הודעות בפולינג.

**מגבלה:** ה-sandbox מוגבל ל-50 הודעות/יום (חלון נע של 24 שעות). לשימוש כבד —
עבור ל[Hermes](HERMES.md).

### הקמה בענן

1. **VM:** צור מכונה קטנה (למשל `e2-micro` ב-Google Cloud, region
   `us-central1`, Ubuntu 24.04; או Oracle Cloud Always Free).
2. **הקמה** — בכפתור **SSH** של ה-VM, פקודה אחת:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/eliezeravihail/chat/main/setup-twilio-vm.sh -o setup.sh && bash setup.sh
   ```
   הסקריפט מתקין הכל, יוצר שירות systemd, ומדפיס את **רשימת הסודות** להוסיף.
3. **סודות** — ‏GitHub → Settings → Secrets and variables → Actions. הוסף:
   `GCP_VM_HOST`, `GCP_VM_USER`, `GCP_VM_SSH_KEY` (מודפסים בסקריפט),
   ו-`OPENROUTER`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`,
   `ALLOWED_WA_ID`. אופציונלי: `REDIS_URL`, `DEFAULT_MODEL`.
   כמשתנה (Variable, לא סוד) אופציונלי: `NTFY_TOPIC` להתראות.
4. **הפעל:** ‏GitHub → Actions → **deploy-gcp** → Run workflow.

מכאן — כל שינוי קוד ב-`main` מתפרס לבד (ראה [למטה](#מה-ה-github-action-עושה)).

### הרצה מקומית

```bash
cp .env.example .env      # מלא את הערכים
pip install -r requirements.txt
python twilio_poll.py
```

### פקודות (בתוך הצ'אט)

| פקודה | פעולה |
| --- | --- |
| `/model <שם>` | החלפת מודל: `hy3`, `claude`, `gpt`, `auto` (חינמי), `deepseek`... |
| `/models` | רשימת המודלים והנוכחי |
| `/credits` | יתרת OpenRouter (נטען / נוצל / נשאר) |
| `/clear` | ניקוי הזיכרון |

ברירת המחדל `hy3`; אם נכשל — נפילה אוטומטית לחינמיים. שליחת תמונה → ניתוח.
המודל נבחר **פר-מספר** (שינוי אצל משתמש אחד לא משפיע על אחר).

### התנהגות מול מגבלת ה-50/יום

כשמזוהה מגבלת ה-sandbox (שגיאה 63038), הבוט **לא מבזבז קריאות LLM בתשלום** על
תשובות שאי אפשר לשלוח: הוא נכנס ל-cooldown (‏`LIMIT_BACKOFF_MIN`, ברירת מחדל
15 דק'), דוחה הודעות חדשות בלי לייצר תשובה, **ועונה עליהן אוטומטית כשהקיבולת
מתפנה**. תשובה שכבר נוצרה ולא נשלחה נשמרת ונשלחת מאוחר יותר — בלי ריצת LLM נוספת.

### הגדרות (משתני סביבה עיקריים)

| משתנה | ברירת מחדל | תפקיד |
| --- | --- | --- |
| `OPENROUTER_KEY` | — | מפתח OpenRouter (חובה) |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM` | — | פרטי Twilio (חובה) |
| `ALLOWED_WA_ID` | — | מספר/ים מורשים, מופרדים בפסיק (חובה) |
| `DEFAULT_MODEL` | `hy3` | מודל ברירת מחדל (slug או קיצור) |
| `REDIS_URL` | — | זיכרון מתמשך (Upstash); בלעדיו זיכרון בזיכרון-תהליך |
| `NTFY_TOPIC` | — | התראות ל-ntfy; ריק = בלי התראות |
| `HEARTBEAT_HOURS` | `6` | תדירות heartbeat ל-ntfy; 0 = כבוי |
| `LIMIT_BACKOFF_MIN` | `15` | דקות המתנה אחרי פגיעה במגבלת ה-50 |

### תפעול ה-VM (SSH)

```bash
sudo systemctl status wa-bot      # מצב
journalctl -u wa-bot -f           # לוגים חיים
sudo systemctl restart wa-bot     # הפעלה מחדש
```

### ניטור — התראות ל-ntfy

הבוט שולח **heartbeat** ל-ntfy כל `HEARTBEAT_HOURS` שעות עם מצב Twilio של
24 השעות האחרונות (התקבלו / נשלחו / נכשלו + מצב המגבלה), וכן התראה בכל פעם
שהודעה נשלחת ונכשלת. אם ה-heartbeat מפסיק להגיע — הבוט או ה-VM למטה. אפשר
לראות בדפדפן ב-`https://ntfy.sh/<topic>` (בלי אפליקציה). בחר topic
לא-ניחוש (הוא מתפקד כסיסמה בערוץ הציבורי).

בנוסף, `monitor-twilio.py` הוא כלי עצמאי שבודק את מצב Twilio ודוחף סיכום
ל-ntfy — שימושי להרצה מתוזמנת (cron) בנפרד מהבוט:

```bash
NTFY_TOPIC=<topic> ./.venv/bin/python monitor-twilio.py
```

---

# גרסה 2 — Hermes (בלי מגבלת הודעות)

סוכן מלא של Nous Research עם מספר WhatsApp ייעודי — **בלי מגבלת הודעות, בלי
Twilio, בלי פייסבוק.** דורש SIM זול חד-פעמי + טלפון ישן.

המדריך המלא, כולל סקריפט הקמה בפקודה אחת וגבולות האבטחה: **[HERMES.md](HERMES.md)**.

---

## מה ה-GitHub Action עושה

הקובץ `.github/workflows/deploy-gcp.yml` הוא **הפריסה האוטומטית**. בכל **push
ל-`main`** (או הפעלה ידנית ב-Actions → deploy-gcp → Run workflow), הוא:

1. מתחבר ל-VM ב-SSH (לפי הסודות `GCP_VM_HOST/USER/SSH_KEY`).
2. מושך את הקוד העדכני (`git pull`).
3. **כותב את קובץ ה-`.env`** על ה-VM מתוך סודות GitHub (המפתחות **לא** נשמרים
   ידנית על השרת — מקור אמת יחיד).
4. מתקין תלויות ומפעיל מחדש את השירות.

### בוחרים מה נפרס — משתנה `DEPLOY_TARGET` (Variable, לא סוד)

מה בדיוק נפרס נקבע ע"י **Repository Variable** בשם `DEPLOY_TARGET`. זה **משתנה
רגיל, לא סוד** — נמצא ב-GitHub → Settings → Secrets and variables → Actions →
לשונית **Variables** → New repository variable.

| ערך | מה נפרס |
| --- | --- |
| `twilio` (ברירת מחדל אם ריק) | בוט ה-Twilio: git pull, כתיבת `.env` מהסודות, restart ל-`wa-bot` |
| `hermes` | סוכן Hermes: git pull, restart ל-gateway של Hermes |
| `off` / `none` | **מכבה את הפריסה האוטומטית** — push לא נוגע ב-VM |

כך שולטים מ-GitHub בלי לגעת בקוד: להשהות פריסות — `off`; לעבור ל-Hermes —
`hermes`. (ה-Action מדלג בשקט אם `GCP_VM_HOST` לא הוגדר.)

---

## רישיון

[MIT](LICENSE)
