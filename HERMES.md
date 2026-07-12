# Hermes Agent בענן חינמי — המסלול המומלץ

מחליף את בוט ה-Twilio (שמוגבל ל-50 הודעות/יום ב-sandbox): סוכן מלא של
[Nous Research](https://github.com/nousresearch/hermes-agent) עם זיכרון מתמשך,
כלים, ו-WhatsApp מובנה — **בלי מגבלת הודעות**. העלות היחידה: טוקנים ב-OpenRouter.

```
WhatsApp (מספר ייעודי) ⇄ Hermes על VM חינמי ⇄ OpenRouter (HY3 → חינמי)
```

> ⚠️ החיבור הוא "מכשיר מקושר" (לא-רשמי) — יש סיכון חסימה למספר. לכן **מספר
> ייעודי בלבד**, לא האישי. הטלפון של מספר הבוט צריך לעלות לרשת פעם ב-~14 יום.

## מה צריך
1. מפתח OpenRouter (יש לך).
2. מספר WhatsApp ייעודי פעיל על טלפון כלשהו.
3. VM חינמי — Google Cloud **e2-micro** (‏1GB; הסקריפט מוסיף swap אוטומטית).

## שלב 1 — VM (פעם אחת, ~10 דק')
<https://console.cloud.google.com> → Compute Engine → Create instance:
**e2-micro**, region `us-central1`, Ubuntu 24.04, דיסק 30GB → Create → כפתור **SSH**.

## שלב 2 — הקמה אוטומטית (סקריפט אחד)
בטרמינל ה-SSH:
```bash
curl -fsSL https://raw.githubusercontent.com/eliezeravihail/chat/main/hermes/setup-hermes-vm.sh -o setup.sh
OPENROUTER_KEY=sk-or-... ALLOWED_NUMBERS=9725XXXXXXXX,9725YYYYYYYY bash setup.sh
```
(`ALLOWED_NUMBERS` = המספרים שמותר להם לדבר עם הבוט — שלך + של החבר, ספרות בלבד.)

הסקריפט מגדיר: swap, התקנת Hermes, ‏OpenRouter, מודל ראשי **tencent/hy3** עם
**נפילה אוטומטית למודלים חינמיים**, אישיות בעברית (SOUL.md), ו-whitelist.

## שלב 3 — חיבור המספר (כשהוא ביד, ~2 דק')
```bash
hermes whatsapp
```
יוצג QR בטרמינל → בטלפון של מספר הבוט: WhatsApp → מכשירים מקושרים → קשר מכשיר
→ סרוק. (הסשן נשמר — סריקה חד-פעמית.)

## שלב 4 — הפעלה קבועה
```bash
hermes gateway run          # בדיקה: שלח הודעה לבוט מהמספר שלך
# עובד? הפוך לשירות שעולה לבד:
sudo env "PATH=$PATH" hermes gateway install --system
sudo env "PATH=$PATH" hermes gateway start --system
```

## תפעול
| פקודה | מה |
| --- | --- |
| `hermes status` / `hermes logs` | מצב ולוגים |
| `hermes model` / `hermes fallback list` | מודל ראשי / שרשרת גיבוי |
| `hermes pairing list` | משתמשים מאושרים |
| עריכת `~/.hermes/SOUL.md` | שינוי האישיות/הסגנון |
| עריכת `~/.hermes/.env` → `WHATSAPP_ALLOWED_USERS` | עדכון המורשים |

אם מודל חינמי ברשימת ה-fallback התיישן — ערוך את `~/.hermes/config.yaml`
(רשימת `fallback_providers`) לכל slug עדכני מ-<https://openrouter.ai/models/?q=free>.

## גבולות אבטחה — מה הבוט יכול ומה לא

שכבות ההגנה שהסקריפט מגדיר:

1. **מי מדבר איתו:** רק מספרים ב-`WHATSAPP_ALLOWED_USERS` (‏`~/.hermes/.env`).
   כל השאר נדחים. שכבה שנייה: `hermes pairing` (אישור ידני).
2. **אילו כלים יש לו:** הסקריפט **מצמצם בכוונה** את ה-toolsets ל: חיפוש ברשת,
   ניתוח תמונות, זיכרון, תזכורות (cron), משימות, חיפוש בשיחות עבר, skills, שאלות
   הבהרה. **מושבת בכוונה:** `terminal` (שורת פקודה על השרת!), `file` (קריאת
   קבצים — כולל `.env` עם המפתח!), `code_execution`, `browser`, `computer_use`.
   ברירת המחדל של Hermes ‏(`hermes-cli`) כוללת את כולם — אל תחזיר אותה בבוט
   שחברים מדברים איתו.
3. **סודות:** המפתח ב-`~/.hermes/.env` ‏(chmod 600). כל עוד `terminal`/`file`
   כבויים — המודל לא יכול להגיע אליו.
4. **בידוד:** הכל רץ על VM נפרד — גם במקרה הגרוע, הנזק תחום לשרת הזה ולקרדיט
   ב-OpenRouter (שאפשר להגביל ב-<https://openrouter.ai/settings/credits>).

להחזרת כלי למתקדמים: הוסף את שמו ל-`toolsets` ב-`config.yaml` והפעל מחדש את
ה-gateway. רשימת הכלים המלאה: `hermes tools` (בטרמינל אינטראקטיבי).
