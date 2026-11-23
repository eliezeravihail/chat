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
| `hermes/setup-hermes-vm.sh` | הקמה ל-VM חדש (x86/ARM): Hermes, הצפנת `~/.hermes`, תמלול קולי, whitelist, שירות |
| `hermes/repair-whatsapp.sh` | חיבור/חיבור-מחדש של וואטסאפ בסדר הנכון (פקודה אחת) |
| `hermes/restore-backup.sh` | שחזור גיבוי מוצפן על מכונה חדשה |
| `hermes/ensure-private-config.py` | אכיפת פרטיות בין משתמשים + ברירות מחדל לתמלול, בכל deploy |
| `.github/workflows/deploy-gcp.yml` | פריסה אוטומטית — push ל-`main` → עדכון SOUL + restart (כל VM עם SSH) |
| `.github/workflows/backup-memory.yml` | גיבוי לילי מוצפן של הזיכרון לריפו פרטי |

## התחלה מהירה

הכל ב-**[HERMES.md](HERMES.md)** — כולל חיבור ה-QR, הצפנת הזיכרון וגבולות
האבטחה. בקצרה:

1. VM חינמי (Oracle Cloud Always Free; גוגל מחייבת על הכתובת) + מספר WhatsApp
   ייעודי על טלפון ישן (חיבור "מכשיר מקושר" — לכן מספר ייעודי, לא האישי).
2. `hermes/setup-hermes-vm.sh`: ‏Hermes, ‏OpenRouter + HY3, תמלול הודעות קוליות
   (Groq), האישיות (`SOUL.md`), ה-whitelist והצפנת הזיכרון.
3. `hermes/repair-whatsapp.sh`: סריקת QR והפעלת השירות, ואז 5 דקות לא נוגעים.
   עריכת האישיות/הסגנון = עריכת `SOUL.md`.

## עדכון אוטומטי (CI)

`.github/workflows/deploy-gcp.yml` פורס בכל **push ל-`main`**: מתחבר ל-VM ב-SSH,
מושך את הקוד, מרענן את `~/.hermes/SOUL.md`, אוכף בידוד-פרטיות בין משתמשים
(‏`group_sessions_per_user` + כיבוי `session_search`/`memory`), ומריץ מחדש את
ה-gateway. הגדרה חד-פעמית ב-GitHub → Settings → Secrets and variables → Actions:

- **סודות:** `GCP_VM_HOST`, `GCP_VM_USER`, `GCP_VM_SSH_KEY` (כל VM עם SSH);
  אופציונלי `GROQ_API_KEY` (תמלול), `WHATSAPP_ALLOWED_USERS` (מורשים).
- **גיבוי לילי מוצפן** (`backup-memory.yml`): ‏`BACKUP_REPO_TOKEN` + ‏Variable
  ‏`BACKUP_REPO` — ראה HERMES.md "גיבוי ושחזור".
- **אופציונלי** (Variables): `DEPLOY_TARGET=off` להשהיית הפריסה (ברירת מחדל
  `hermes`); `HERMES_UPGRADE=1` לעדכון גרסה חד-פעמי; `HERMES_WIPE_MEMORY=1`
  למחיקת זיכרון גורפת חד-פעמית. פרטים ב-**[HERMES.md](HERMES.md)**.

## רישיון

[MIT](LICENSE)
