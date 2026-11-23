# Hermes Agent בענן חינמי — המסלול המומלץ

בוט WhatsApp פרטי מבוסס סוכן מלא של
[Nous Research](https://github.com/nousresearch/hermes-agent) עם זיכרון מתמשך,
כלים, ו-WhatsApp מובנה — **בלי מגבלת הודעות**. העלות היחידה: טוקנים ב-OpenRouter.

```
WhatsApp (מספר ייעודי) ⇄ Hermes על VM חינמי ⇄ OpenRouter (HY3 → חינמי)
                              ↳ הודעות קוליות → טקסט (Groq Whisper, חינמי)
```

> ⚠️ החיבור הוא "מכשיר מקושר" (לא-רשמי) — יש סיכון חסימה למספר. לכן **מספר
> ייעודי בלבד**, לא האישי. הטלפון של מספר הבוט צריך לעלות לרשת פעם ב-~14 יום.

## מה צריך
1. מפתח OpenRouter (יש לך).
2. מספר WhatsApp ייעודי פעיל על טלפון כלשהו.
3. VM חינמי — **Oracle Cloud Always Free** (מומלץ, ראה למטה) או Google Cloud e2-micro.
4. אופציונלי: מפתח **Groq** חינמי (<https://console.groq.com>) לתמלול הודעות קוליות.
5. מפתח הצפנה לזיכרון: `openssl rand -base64 32` פעם אחת → שמור כסוד
   `HERMES_MEMORY_KEY` ב-GitHub. אותו ערך עובר לסקריפט ההקמה, וכך גיבויים
   ניתנים לשחזור על מכונה חדשה.

## שלב 1 — VM (פעם אחת, ~10 דק')

**Oracle Cloud Always Free (0 ₪, גם הכתובת וגם הדיסק):** <https://cloud.oracle.com>
→ Compute → Instances → Create: Shape **Ampere (VM.Standard.A1.Flex)**, ‏1–4 OCPU,
‏6–24GB; Image **Ubuntu 24.04** (aarch64); השאר "Assign a public IPv4 address"
מסומן; הורד את מפתח ה-SSH. אם "Out of capacity" — נסה שוב מאוחר יותר או Availability
Domain אחר. המשתמש הוא `ubuntu`. SSH מהדפדפן: Instance → Console connection →
Cloud Shell, או כל לקוח SSH עם המפתח.

**Google Cloud (חלופה):** e2-micro ב-`us-central1`, דיסק **Standard** 30GB, Ubuntu
24.04. ⚠️ המכונה עצמה חינמית, אבל גוגל מחייבת על כתובת IPv4 חיצונית (~13 ₪
לחודש) ועל דיסק Balanced. לכן אורקל.

## שלב 2 — הקמה אוטומטית (סקריפט אחד)
בטרמינל ה-SSH:
```bash
git clone https://github.com/eliezeravihail/chat ~/chat
OPENROUTER_KEY=sk-or-... GROQ_KEY=gsk_... HERMES_MEMORY_KEY='<הערך מהסוד>' \
  ALLOWED_NUMBERS=9725XXXXXXXX,9725YYYYYYYY bash ~/chat/hermes/setup-hermes-vm.sh
```
(`ALLOWED_NUMBERS` = המספרים שמותר להם לדבר עם הבוט — שלך + של החבר, ספרות בלבד.
‏`GROQ_KEY` ו-`HERMES_MEMORY_KEY` אופציונליים אך מומלצים.) הסקריפט עובד גם על ARM.

הסקריפט מגדיר: swap (רק במכונות קטנות), התקנת Hermes, ‏OpenRouter, מודל ראשי
**tencent/hy3** עם **נפילה אוטומטית למודלים חינמיים**, תמלול קולי דרך Groq,
הצפנת `~/.hermes`, אישיות **פסיכותרפיסט בשם אהרון** בעברית (SOUL.md — גישה
ממוקדת-אדם ומבוססת-אמונה, עם גבולות ברורים והפניה לעזרה במצוקה), whitelist,
ושירות gateway (מותקן, לא מופעל עד הסריקה).

## שלב 3 — חיבור המספר והפעלה (פקודה אחת, ~3 דק')
```bash
bash ~/chat/hermes/repair-whatsapp.sh
```
הסקריפט עוצר כל תהליך קודם, מנקה סשן ישן, מריץ `hermes whatsapp` ומפעיל את
השירות מיד אחרי "Pairing complete". יוצג QR → בטלפון של מספר הבוט: WhatsApp →
מכשירים מקושרים → קשר מכשיר → **סרוק את ה-QR הראשון מיד**.

**ואז 5 דקות לא נוגעים בכלום.** בלי Ctrl+C, בלי restart, בלי `hermes gateway`.
WhatsApp משלימה את רישום המכשיר בדקות הראשונות; הפסקה באמצע, או שני תהליכים על
אותו סשן, גורמים ל-"Logged out" ולסריקה מחדש (כך נשבר החיבור באוגוסט 2026, שוב
ושוב). אחרי 5 דקות: המכשיר מופיע ב"מכשירים מקושרים", ושולחים הודעת בדיקה.

לניתוק עתידי: אותה פקודה. לאתחול נקי בלי סריקה: `repair-whatsapp.sh --keep`.

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

## הודעות קוליות

הודעה קולית שנשלחת לבוט מתומללת אוטומטית (Hermes מובנה; הספק: **Groq**,
מודל `whisper-large-v3`, עברית) ונכנסת לשיחה כטקסט. בנוסף, התמלול הגולמי נשלח
חזרה לצ'אט (‏🎙️ "…"), כך שמי שמעדיף לקרוא מקבל טקסט. המפתח: סוד `GROQ_API_KEY`
ב-GitHub (מסונכרן ל-`~/.hermes/.env` בכל deploy) או `GROQ_KEY` בהקמה. בלי מפתח
הבוט עונה שההקלטה לא תומללה. לא להשתמש בתמלול מקומי (`provider: local`) על
מכונה חינמית — Whisper שמבין עברית צריך מעבד חזק. להגדרות: בלוק `stt` ב-
`~/.hermes/config.yaml` (‏`echo_transcripts: false` מבטל את ההד).

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

## גיבוי ושחזור

מחיקת ה-VM = מחיקת הזיכרון, אלא אם מגבים. `.github/workflows/backup-memory.yml`
מושך כל לילה צילום עקבי של `state.db` (‏+ `memories/` + קרדנציאלי הוואטסאפ),
מצפין אותו ב-AES-256 **עם מפתח ההצפנה של המכונה** (`~/.hermes.key` =
הסוד `HERMES_MEMORY_KEY`), ומעלה אותו לריפו **פרטי** נפרד, 14 אחרונים. שום דבר
לא מודפס ללוג. הגדרה חד-פעמית:

1. ריפו פרטי ריק, למשל `<you>/chat-backups`.
2. טוקן Fine-grained לריפו הזה בלבד, ‏Contents: Read and write.
3. בריפו הזה: Secret ‏`BACKUP_REPO_TOKEN`, ‏Variable ‏`BACKUP_REPO=<you>/chat-backups`.

שחזור על מכונה חדשה (אחרי `setup-hermes-vm.sh` עם אותו `HERMES_MEMORY_KEY`):
```bash
bash ~/chat/hermes/restore-backup.sh hermes-YYYYMMDD-HHMM.tar.enc            # זיכרון בלבד
bash ~/chat/hermes/restore-backup.sh hermes-....tar.enc --with-whatsapp     # + החיבור, בלי QR
```
`--with-whatsapp` רק כשהמכונה הישנה כבר לא קיימת — שתי מכונות על אותו קישור =
ניתוק מיידי. חלופה בלי הגדרות: באורקל, Boot volume → Create backup (חינם, עד 5).

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
agent:
  disabled_toolsets: [session_search, memory, browser, spotify, web]
```

**⚠️ הכלי שעוקף את הבידוד — `session_search` / `memory`.** ל-Hermes יש כלי
שמחפש/משחזר שיחות עבר (`session_search`) וכלי זיכרון-פרופיל (`memory`). **אין
בהם שום סינון לפי משתמש** — הם קוראים ישירות מ-`state.db` וסורקים את **כל**
הסשנים (אפילו חוצה-פרופילים). כלומר, גם אם הבידוד תקין לגמרי, המודל יכול להריץ
`session_search` ולמשוך את השיחה של החבר ("מה אתה יודע עליי" → מידע של מישהו
אחר). **על בוט רב-משתמשים חובה לכבות אותם.** לכן הם נמצאים ב-`disabled_toolsets`
(denylist גלובלי שמנצח כל allowlist), וה-CI אוכף זאת בכל deploy דרך
`hermes/ensure-private-config.py`. הכיבוי **לא** פוגע ברצף השיחה — התמליל השוטף
הוא חלק מהסשן, לא מכלי ה-`memory`.

> ⚠️ **אם ראית ערבוב מידע בצ'אט פרטי (DM)** — שני חשודים:
> 1. **הכלי `session_search`/`memory` היה פעיל** (הכי סביר, לפי ההתנהגות) →
>    מכובה עכשיו אוטומטית ב-`disabled_toolsets`.
> 2. **גרסה ישנה** שמקריסה DMs לסשן משותף → הדליקו `HERMES_UPGRADE=1` (ראה
>    "עדכון אוטומטי"), deploy אחד, ואז לריק.
>
> בשני המקרים הכיבוי/העדכון עוצר **מכאן והלאה** אבל **לא מנקה** מה שכבר נשמר
> ב-`state.db`. לניקוי: **`/new` משני הטלפונים** (מפסיק שימוש בהיסטוריה), או
> **מחיקה גורפת** — הדליקו `HERMES_WIPE_MEMORY=1` (ראה "עדכון אוטומטי"), deploy
> אחד, והחזירו לריק. זה מאפס את הזיכרון של **כל** המשתמשים (הקובץ נשמר בגיבוי
> `state.db.wiped.*` על ה-VM, לא נמחק פיזית).

## תגובה בקבוצה

ברירת המחדל של Hermes ל-`group_policy` היא **`pairing`** — הבוט **מתעלם** מהודעות
בקבוצה עד שהקבוצה מאושרת. לכן הוא שתק בקבוצה גם כשפנו אליו. ההגדרה (ב-`config.yaml`,
נאכפת גם ב-CI דרך `ensure-private-config.py`):

```yaml
whatsapp:
  group_policy: open          # מעבד הודעות בקבוצות (במקום pairing)
  require_mention: true        # מגיב רק כשפונים אליו
  mention_patterns: ["אהרון"]  # פנייה בשם (בנוסף ל-@mention או reply)
```

- **מתי הוא מגיב:** רק כשפונים אליו — @mention, תגובה (reply) להודעה שלו, או הזכרת
  השם "אהרון". לא לכל הודעה בקבוצה (זה היה רועש ויקר, ולא רצוי לבוט תרפיה).
- **זיכרון בקבוצה:** מבודד פר-משתתף (`group_sessions_per_user: true`) — כל אחד
  מדבר עם זיכרון משלו, גם בקבוצה.
- **⚠️ טווח:** ‏`WHATSAPP_ALLOWED_USERS` (הרשימה הלבנה) חלה על **צ'אטים פרטיים
  בלבד** — בקבוצות הגישה נשלטת ע"י `group_policy`. עם `open`, **כל** מי שבקבוצה
  יכול להפעיל את הבוט ע"י פנייה אליו. אם זה מטריד, עברו ל:
  ```yaml
  whatsapp:
    group_policy: allowlist
    group_allow_from: ["<group-jid>@g.us"]   # רק הקבוצה הזו
  ```
  (את ה-JID של הקבוצה אפשר לראות ב-`hermes logs` כשמגיעה הודעה מהקבוצה.)

## גבולות אבטחה — מה הבוט יכול ומה לא

שכבות ההגנה שהסקריפט מגדיר:

1. **מי מדבר איתו:** רק מספרים ב-`WHATSAPP_ALLOWED_USERS` (‏`~/.hermes/.env`).
   כל השאר נדחים. שכבה שנייה: `hermes pairing` (אישור ידני).
2. **אילו כלים יש לו:** רצף השיחה (התמליל) הוא חלק מהסשן — לא כלי — אז הוא נשאר.
   כלים כבויים גלובלית דרך `agent.disabled_toolsets`: **`session_search` ו-`memory`
   (קריטי לפרטיות — קוראים על פני כל המשתמשים; ראה "בידוד זיכרון בין משתמשים")**,
   ‏`browser` (כבד על 1GB), `spotify` (דורש מפתחות), `web`. ופקודות-הסקיל
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
    disabled_toolsets: [session_search, memory, browser, spotify, web]
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

- `GCP_VM_HOST`, `GCP_VM_USER`, `GCP_VM_SSH_KEY` — SSH רגיל; השמות היסטוריים,
  עובד מול כל VM (אורקל, גוגל). ב-Oracle המשתמש הוא `ubuntu`.
- אופציונלי (Secret): `GROQ_API_KEY` — תמלול הודעות קוליות (ראה "הודעות קוליות").
- אופציונלי (Secret): `WHATSAPP_ALLOWED_USERS` — המורשים, מנוהלים מ-GitHub.
- גיבוי לילי: `BACKUP_REPO_TOKEN` + ‏`BACKUP_REPO` (ראה "גיבוי ושחזור").
- אופציונלי (Variable): `DEPLOY_TARGET=off` להשהיית הפריסה. ברירת המחדל היא
  `hermes`, אז אין צורך להגדירו כדי שהפריסה תעבוד.
- אופציונלי (Variable): `HERMES_UPGRADE=1` — עדכון חד-פעמי של גרסת Hermes
  ב-deploy הבא (למשל אם בידוד הזיכרון לא נאכף בגרסה ישנה). אחרי ה-deploy החזירו
  את הערך לריק כדי לא לעדכן בכל push (סחף גרסאות עלול לשבור בוט תקין).
- אופציונלי (Variable): `HERMES_WIPE_MEMORY=1` — **מחיקה גורפת** חד-פעמית של כל
  הזיכרון (מעביר את `state.db` לגיבוי `state.db.wiped.*`, נוצר חדש ריק ב-restart).
  מאפס את **כל** המשתמשים. אחרי ה-deploy החזירו לריק.

בכל deploy ה-CI גם: (א) מוודא `group_sessions_per_user: true`; (ב) מריץ
`hermes/ensure-private-config.py` שמכריח `session_search`+`memory` להיות ב-
`disabled_toolsets` — כדי שהמודל לא יוכל לחפש בסשן של משתמש אחר. ראה "בידוד
זיכרון בין משתמשים".

אז כל push מושך את הריפו, מרענן את `~/.hermes/SOUL.md` ומריץ מחדש את ה-gateway
(שירות-משתמש, `systemctl --user`) — אוטומטית, בלי לגעת ידנית. (מדלג בשקט אם
`GCP_VM_HOST` לא הוגדר.)
