# Hermes Agent בענן חינמי — המסלול המומלץ

בוט WhatsApp פרטי מבוסס סוכן מלא של
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
**נפילה אוטומטית למודלים חינמיים**, אישיות **פסיכותרפיסט בשם אהרון** בעברית
(SOUL.md — גישה ממוקדת-אדם ומבוססת-אמונה, עם גבולות ברורים והפניה לעזרה
במצוקה), ו-whitelist.

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

## הצפנה

| קטע | הצפנה |
| --- | --- |
| וואטסאפ: טלפון המשתמש ⇄ ה-VM | קצה-לקצה (Signal protocol) — גם Meta לא רואה |
| ה-VM ⇄ OpenRouter/מודל | TLS; ספק המודל מעבד את הטקסט (בלתי נמנע בכל בוט LLM) |
| **הזיכרון במנוחה על ה-VM** | **מוצפן** — `~/.hermes` הוא **gocryptfs** |

**זיכרון מוצפן במנוחה:** ‏Hermes תמיד כותב את התמלילים ל-`~/.hermes/state.db`.
הסקריפט מגדיר את `~/.hermes` כ-**gocryptfs**: על הדיסק יש רק ciphertext
(‏`~/.hermes.cipher`), הפענוח **עצל, פר-קובץ, ורק ב-RAM** כשמותקן. מפתח ב-
`~/.hermes.key` ‏(‏0600; אפשר לספק דרך הסוד `HERMES_MEMORY_KEY`). מותקן אוטומטית
באתחול (שירות `hermes-crypt`). כך **אין קבצים פתוחים עם תוכן שיחות על המחשב**.
(זה למטרת "לא לשמור פליינטקסט", לא נגד גניבת הדיסק — לשם כך צריך מפתח מחוץ למכונה.)

## זיכרון שיחה ואיפוס

- **זיכרון:** ‏Hermes שומר את השיחה **אוטומטית וללא הגבלת זמן** (ברירת מחדל:
  אף פעם לא מתאפס לבד; הקשר ארוך נדחס אוטומטית). זה עובד גם עם אפס כלים —
  תמליל השיחה הוא לא "כלי", הוא חלק מהסשן.
- **איפוס יזום:** המשתמש שולח **`/new`** (או `/reset`) בצ'אט — וההקשר מתאפס.
  ה-SOUL מנחה את המודל להסביר זאת למי שמבקש "תשכח את השיחה".
- **"ניקוי צ'אט" בוואטסאפ:** ⚠️ לא ניתן לזיהוי. מחיקת שיחה בוואטסאפ היא פעולה
  מקומית בטלפון של המשתמש — שום אות לא נשלח לצד השני (לא ב-API הרשמי ולא
  ב-Baileys). לכן הבוט ימשיך לזכור עד שישלחו לו `/new`. אם רוצים איפוס אוטומטי
  תקופתי אפשר להגדיר `session_reset` (מצב `daily`/`idle`) ב-config.

## בידוד זיכרון בין משתמשים

**כל משתמש מקבל זיכרון נפרד לחלוטין.** ‏Hermes מפריד סשנים לפי שולח:

- **צ'אט פרטי (DM):** מפתח לפי מספר הטלפון —
  `agent:main:whatsapp:dm:{מספר}`. השיחה שלך והשיחה של החבר הן שני עולמות
  נפרדים; הבוט לא יכול "לזלוג" מידע מאחד לשני.
- **בקבוצה:** מפתח לפי המשתתף כשהדגל `group_sessions_per_user: true` (ברירת
  המחדל). כל אחד בקבוצה מדבר עם זיכרון משלו.

הדגלים (מפתחות גלובליים ב-`~/.hermes/config.yaml`; הסקריפט וה-CI כבר קובעים
אותם מפורשות כדי שעריכה ידנית לא תכבה פרטיות בשקט):

```yaml
group_sessions_per_user: true    # בידוד פר-משתמש בקבוצות (ברירת מחדל)
thread_sessions_per_user: false
```

> ⚠️ **אם ראית ערבוב מידע בין משתמשים** — סימן שהסשן היה משותף בעבר (גרסה ישנה
> או `group_sessions_per_user: false`). קביעת הדגל מונעת ערבוב **מכאן והלאה**,
> אבל **לא מנקה למפרע** תמליל שכבר התערבב. לכן אחרי ה-deploy: **שלחו `/new` משני
> הטלפונים** כדי לאפס את הסשנים ולהתחיל נקי. אם עדיין מתערבב — הגרסה המותקנת
> קדומה מדי; הדליקו את המשתנה `HERMES_UPGRADE=1` (ראה "עדכון אוטומטי"), עשו
> deploy אחד, והחזירו אותו לריק.

## גבולות אבטחה — מה הבוט יכול ומה לא

שכבות ההגנה שהסקריפט מגדיר:

1. **מי מדבר איתו:** רק מספרים ב-`WHATSAPP_ALLOWED_USERS` (‏`~/.hermes/.env`).
   כל השאר נדחים. שכבה שנייה: `hermes pairing` (אישור ידני).
2. **אילו כלים יש לו:** בערוץ ה-WhatsApp מופעל סט מצומצם בלבד (זיכרון והקשר
   להמשכיות). כלים כבדים/מיותרים כבויים גלובלית דרך `agent.disabled_toolsets`
   (‏`browser` — כבד על 1GB, `spotify` — דורש מפתחות, `web`), ופקודות-הסקיל
   המובנות (~69, כמו `/claude-code`, `/arxiv`) כבויות ב-`hermes skills opt-out
   --remove` (ראה "כוונון" למטה). **תמיד מושבתים:** `terminal` (שורת פקודה על
   השרת!), `file` (קריאת קבצים — כולל `.env` עם המפתח!), `code_execution`,
   `computer_use` — אל תפעיל אותם.
3. **גבולות תוכן:** ‏SOUL.md מנחה את המודל לא לנהל שיחות ארוטיות/מיניות —
   לסרב בנימוס ולהציע נושא אחר.
4. **סודות:** המפתח ב-`~/.hermes/.env` ‏(chmod 600). כל עוד `terminal`/`file`
   כבויים — המודל לא יכול להגיע אליו.
5. **בידוד:** הכל רץ על VM נפרד — גם במקרה הגרוע, הנזק תחום לשרת הזה ולקרדיט
   ב-OpenRouter (שאפשר להגביל ב-<https://openrouter.ai/settings/credits>).

להחזרת כלי למתקדמים: הוסף את שמו ל-`toolsets` ב-`config.yaml` והפעל מחדש את
ה-gateway. רשימת הכלים המלאה: `hermes tools` (בטרמינל אינטראקטיבי).

## כוונון: מהירות, כלים וסקילים

- **מהירות:** HY3 עם "חשיבה" (reasoning) פעילה איטי מיותר לשיחת תמיכה. לכיבוי,
  הוסף ל-`~/.hermes/config.yaml`:
  ```yaml
  agent:
    reasoning_effort: "none"      # none|minimal|low|medium|high|... (ברירת מחדל: medium)
    disabled_toolsets: [browser, spotify, web]
  ```
  (חלופה מהצ'אט, מהמספר שלך: `/reasoning none --global`.) `disabled_toolsets`
  מוריד כלי גם אם ערוץ עדיין מפרט אותו.
- **סקילים (פקודות `/`):** ההתקנה הרשמית מפעילה ~69 פקודות-סקיל שנחשפות למשתמש
  ושוברות את האישיות. לכיבוי מלא:
  ```bash
  hermes skills opt-out --remove   # --remove מוחק גם קיימים; בלעדיו רק עוצר עתידיים
  systemctl --user restart hermes-gateway
  ```
- **פקודות מובנות:** `/new`, `/help`, `/retry` נתפסות ע"י Hermes *לפני* המודל
  ואי אפשר להסתירן דרך SOUL. **`/new`** (או `/reset`) מאפס את השיחה — ה-`/clear`
  הישן של Twilio *אינו* קיים ב-Hermes. איפוס כזה גם מנקה זהות ישנה שנתקעה
  בזיכרון השיחה (אם הבוט "נתקע" על שם קודם — `/new` פותר).

## עדכון אוטומטי (CI)

`.github/workflows/deploy-gcp.yml` מריץ deploy בכל push ל-main. כל שנדרש הוא
הסודות ב-GitHub → Settings → Secrets and variables → Actions → Secrets:

- `GCP_VM_HOST`, `GCP_VM_USER`, `GCP_VM_SSH_KEY`.
- אופציונלי (Variable): `DEPLOY_TARGET=off` להשהיית הפריסה. ברירת המחדל היא
  `hermes`, אז אין צורך להגדירו כדי שהפריסה תעבוד.
- אופציונלי (Variable): `HERMES_UPGRADE=1` — עדכון חד-פעמי של גרסת Hermes
  ב-deploy הבא (למשל אם בידוד הזיכרון לא נאכף בגרסה ישנה). אחרי ה-deploy החזירו
  את הערך לריק כדי לא לעדכן בכל push (סחף גרסאות עלול לשבור בוט תקין).

בכל deploy ה-CI גם מוודא ש-`group_sessions_per_user: true` ב-`config.yaml`
(בידוד זיכרון פר-משתמש) — ראה "בידוד זיכרון בין משתמשים".

אז כל push מושך את הריפו, מרענן את `~/.hermes/SOUL.md` ומריץ מחדש את ה-gateway
(שירות-משתמש, `systemctl --user`) — אוטומטית, בלי לגעת ידנית. (מדלג בשקט אם
`GCP_VM_HOST` לא הוגדר.)
