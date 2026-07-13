# chat — בוט WhatsApp חכם בעברית

בוט אישי שמחבר WhatsApp למודלי שפה (HY3 / Claude / GPT / חינמיים). שיחה טבעית
בעברית, זיכרון, ושאלות על תמונות.

יש **שתי גרסאות** — בחר אחת:

| גרסה | יתרון | חיסרון | מדריך |
| --- | --- | --- | --- |
| **1 · Twilio** (רצה עכשיו) | הכי פשוט, רשמי, בלי סיכון חסימה | מגבלת **50 הודעות/יום** (sandbox) | כאן למטה ⬇️ |
| **2 · Hermes** (מתקדם) | **בלי מגבלת הודעות**, סוכן מלא | דורש מספר WhatsApp ייעודי + טלפון ישן | [HERMES.md](HERMES.md) |

שתי הגרסאות רצות על אותו **VM חינמי** של Google Cloud (e2-micro).

---

## מבנה המאגר — מה כל קובץ

| קובץ | תפקיד | שייך ל |
| --- | --- | --- |
| `core.py` | המוח: מודלים, זיכרון, פקודות, עברית | Twilio |
| `twilio_poll.py` | הבוט — מושך הודעות מ-Twilio ועונה | Twilio |
| `setup-twilio-vm.sh` | הקמת ה-VM בפקודה אחת | Twilio |
| `.github/workflows/deploy-gcp.yml` | פריסה אוטומטית (ראה [למטה](#מה-ה-github-action-עושה)) | Twilio |
| `.env.example` | דוגמת הגדרות (להרצה מקומית) | Twilio |
| `requirements.txt` | תלויות Python | Twilio |
| `hermes/setup-hermes-vm.sh` | הקמת Hermes בפקודה אחת | Hermes |
| `HERMES.md` | המדריך המלא ל-Hermes | Hermes |

---

# גרסה 1 — Twilio

**מה זה:** הבוט הפשוט שלנו (`twilio_poll.py`) שמדבר עם WhatsApp דרך ה-sandbox
של Twilio, ועם המודלים דרך OpenRouter. **זו הגרסה שרצה אצלך עכשיו.**

**מגבלה:** ה-sandbox מוגבל ל-50 הודעות/יום. לשימוש כבד — עבור ל[Hermes](HERMES.md).

### איך זה רץ בענן (מה שכבר עשית)

1. **VM:** ‏<https://console.cloud.google.com> → Compute Engine → Create instance
   → `e2-micro`, region `us-central1`, Ubuntu 24.04.
2. **הקמה** — בכפתור **SSH** של ה-VM, פקודה אחת:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/eliezeravihail/chat/main/setup-twilio-vm.sh -o setup.sh && bash setup.sh
   ```
   הסקריפט מתקין הכל, יוצר שירות systemd, ומדפיס את **רשימת הסודות** להוסיף.
3. **סודות** — ‏GitHub → Settings → Secrets and variables → Actions. הוסף:
   `GCP_VM_HOST`, `GCP_VM_USER`, `GCP_VM_SSH_KEY` (מודפסים בסקריפט),
   ו-`OPENROUTER`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM`,
   `ALLOWED_WA_ID` (הערכים שלך). אופציונלי: `REDIS_URL`, `DEFAULT_MODEL`.
4. **הפעל:** ‏GitHub → Actions → **deploy-gcp** → Run workflow.

מכאן — כל שינוי קוד ב-`main` מתפרס לבד (ראה [למטה](#מה-ה-github-action-עושה)).

### פקודות (בתוך הצ'אט)

| פקודה | פעולה |
| --- | --- |
| `/model <שם>` | החלפת מודל: `hy3`, `claude`, `gpt`, `auto` (חינמי), `deepseek`... |
| `/models` | רשימת המודלים והנוכחי |
| `/credits` | יתרת OpenRouter (נטען / נוצל / נשאר) |
| `/clear` | ניקוי הזיכרון |

ברירת המחדל `hy3`; אם נכשל — נפילה אוטומטית לחינמיים. שליחת תמונה → ניתוח.
המודל נבחר **פר-מספר** (השינוי שלך לא משפיע על משתמש אחר).

### תפעול ה-VM (SSH)

```bash
sudo systemctl status wa-bot      # מצב
journalctl -u wa-bot -f           # לוגים חיים
sudo systemctl restart wa-bot     # הפעלה מחדש
```

### ניטור — האם הגעת למגבלת 50/יום? (התראה ל-ntfy)

`monitor-twilio.py` בודק את פעילות Twilio של היום (כמה נשלח, ואילו שגיאות —
במיוחד `63038` = מגבלת ה-50) ודוחף סיכום ל-**ntfy** — התראה לטלפון שעובדת גם
כשה-WhatsApp חסום. אפשר לראות בדפדפן ב-`https://ntfy.sh/<topic>` (בלי אפליקציה):

```bash
cd ~/chat
# בחר topic כלשהו לא-ניחוש (הוא מתפקד כסיסמה בערוץ הציבורי):
NTFY_TOPIC=eli-bot-7hK2p ./.venv/bin/python monitor-twilio.py
# כל שעה אוטומטית:
( crontab -l 2>/dev/null; echo "0 * * * * cd ~/chat && NTFY_TOPIC=eli-bot-7hK2p ./.venv/bin/python monitor-twilio.py" ) | crontab -
```

---

# גרסה 2 — Hermes (בלי מגבלת הודעות)

סוכן מלא של Nous Research על אותו VM, עם מספר WhatsApp ייעודי — **בלי מגבלת
הודעות, בלי Twilio, בלי פייסבוק.** דורש SIM זול חד-פעמי + טלפון ישן.

המדריך המלא, כולל סקריפט הקמה בפקודה אחת וגבולות האבטחה: **[HERMES.md](HERMES.md)**.

---

## מה ה-GitHub Action עושה

הקובץ `.github/workflows/deploy-gcp.yml` הוא **הפריסה האוטומטית**. בכל **push
ל-`main`** (או הפעלה ידנית ב-Actions → deploy-gcp → Run workflow), הוא:

1. מתחבר ל-VM שלך ב-SSH (לפי הסודות `GCP_VM_HOST/USER/SSH_KEY`).
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

כך אתה שולט מ-GitHub, בלי לגעת בקוד: רוצה להשהות פריסות? שים `off`. עברת ל-
Hermes? שים `hermes`. (ה-Action מדלג בשקט אם `GCP_VM_HOST` לא הוגדר.)

---

## רישיון

[MIT](LICENSE) © 2026 Eliezer Avihail
