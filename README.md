# chat — אהרון, בוט WhatsApp בעברית (Hermes)

בוט WhatsApp פרטי שמריץ סוכן [Hermes](https://github.com/nousresearch/hermes-agent)
של Nous Research על VM חינמי, מול מודלי OpenRouter (ברירת מחדל **HY3** עם נפילה
אוטומטית למודלים חינמיים). האישיות: **אהרון** — נוכחות תומכת ומקצועית בעברית
(מוגדרת ב-`SOUL.md`). **בלי מגבלת הודעות, בלי Twilio, בלי פייסבוק.** הגישה
מוגבלת למספרים מורשים בלבד, והזיכרון מוצפן במנוחה.

## מבנה המאגר

| קובץ | תפקיד |
| --- | --- |
| `SOUL.md` | האישיות של אהרון — **מקור אמת יחיד**, נטען ע"י Hermes (`~/.hermes/SOUL.md`) |
| `HERMES.md` | **המדריך המלא**: הקמה, חיבור WhatsApp, הצפנה, כלים, whitelist, כוונון ו-CI |
| `hermes/setup-hermes-vm.sh` | עזר הקמה ל-VM (swap, הצפנת `~/.hermes` ב-gocryptfs, whitelist) |
| `.github/workflows/deploy-gcp.yml` | פריסה אוטומטית — push ל-`main` → עדכון SOUL + restart |

## התחלה מהירה

הכל ב-**[HERMES.md](HERMES.md)** — כולל חיבור ה-QR, הצפנת הזיכרון וגבולות
האבטחה. בקצרה:

1. VM חינמי (Google Cloud e2-micro, ‏1GB) + מספר WhatsApp ייעודי על טלפון ישן
   (חיבור "מכשיר מקושר" — לכן מספר ייעודי, לא האישי).
2. התקנת Hermes, הגדרת OpenRouter + HY3, האישיות (`SOUL.md`) וה-whitelist.
3. חיבור ה-QR והפעלת שירות ה-gateway. עריכת האישיות/הסגנון = עריכת `SOUL.md`.

## עדכון אוטומטי (CI)

`.github/workflows/deploy-gcp.yml` פורס בכל **push ל-`main`**: מתחבר ל-VM ב-SSH,
מושך את הקוד, מרענן את `~/.hermes/SOUL.md`, ומריץ מחדש את ה-gateway (שירות-משתמש).
הגדרה חד-פעמית ב-GitHub → Settings → Secrets and variables → Actions:

- **סודות:** `GCP_VM_HOST`, `GCP_VM_USER`, `GCP_VM_SSH_KEY`.
- **אופציונלי** (Variable): `DEPLOY_TARGET=off` להשהיית הפריסה. ברירת המחדל
  היא `hermes`, אז אין צורך להגדירו כדי שהפריסה תעבוד. (הפעולה מדלגת בשקט אם
  `GCP_VM_HOST` לא הוגדר.)

## רישיון

[MIT](LICENSE)
