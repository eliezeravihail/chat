# chat — WhatsApp ⇄ OpenRouter bridge

גשר קטן שמחבר את **WhatsApp** (דרך Meta Cloud API) אל **OpenRouter**, כך שאפשר
לשוחח עם מודלי שפה שונים ישירות מתוך צ'אט וואטסאפ. הבוט מוגבל למשתמש מורשה יחיד.

A small bridge that connects **WhatsApp** (via the Meta Cloud API) to
**OpenRouter**, letting you chat with various LLMs straight from WhatsApp.
Locked to a single authorized user.

## Features

- מענה של מודל שפה לכל הודעת טקסט נכנסת (למשתמש המורשה בלבד).
- זיכרון שיחה של 12 תורים אחרונים (user + assistant).
- החלפת מודל בזמן אמת דרך פקודות.
- אימות חתימה `X-Hub-Signature-256` על כל webhook.
- חלוקת תשובות ארוכות לצ'אנקים (מגבלת 4096 תווים של וואטסאפ).

## Commands

בתוך הצ'אט בוואטסאפ:

| פקודה            | פעולה                                             |
| ---------------- | ------------------------------------------------- |
| `/models`        | הצגת המודלים הזמינים והמודל הנוכחי                 |
| `/model <שם>`    | החלפת מודל (לפי alias או מזהה OpenRouter מלא)     |
| `/model`         | הצגת המודל הנוכחי                                  |
| `/clear`         | ניקוי הקשר השיחה                                   |

Aliases זמינים: `claude`, `gpt`, `gemini`, `deepseek`, `llama`, `qwen`.

## Environment variables

ראה `.env.example`. משתנים נדרשים:

| משתנה            | תיאור                                                          |
| ---------------- | -------------------------------------------------------------- |
| `WA_TOKEN`       | Meta permanent access token                                    |
| `WA_PHONE_ID`    | Phone number ID מ-Meta Business                                |
| `WA_VERIFY_TOKEN`| מחרוזת שרירותית; חייבת להתאים למה שמזינים ב-UI של Meta         |
| `WA_APP_SECRET`  | App secret (לאימות `X-Hub-Signature-256`)                     |
| `ALLOWED_WA_ID`  | ה-wa_id שלך, למשל `9725XXXXXXXX`                              |
| `OPENROUTER_KEY` | OpenRouter API key                                            |
| `REDIS_URL`      | Upstash `redis://` URL (אופציונלי; נופל חזרה לזיכרון פנימי)   |

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ומלא את הערכים
set -a; source .env; set +a
uvicorn wa_bot:app --host 0.0.0.0 --port 8080
```

חשוף את הפורט לאינטרנט (למשל `ngrok http 8080`) והזן את ה-URL
`https://.../webhook` ב-Meta Business כ-callback, עם `WA_VERIFY_TOKEN` כ-verify token.

## Deploy

הפרויקט כולל `Procfile` ומתאים לפלטפורמות כמו Railway / Render / Fly:

```
web: uvicorn wa_bot:app --host 0.0.0.0 --port ${PORT:-8080}
```

הגדר את משתני הסביבה בפאנל של הפלטפורמה והצבע את webhook של Meta ל-`https://<your-app>/webhook`.

## Endpoints

| נתיב         | שיטה | תיאור                                    |
| ------------ | ---- | ---------------------------------------- |
| `/webhook`   | GET  | אימות webhook של Meta (hub.challenge)    |
| `/webhook`   | POST | קבלת הודעות נכנסות                        |
| `/health`    | GET  | בדיקת בריאות                              |

## Notes

- ה-webhook תמיד מחזיר `200` מהר, ומעבד את ההודעה ברקע — Meta עושה retry על timeout,
  מה שהיה גורם לתשובות כפולות.
- מצב ברירת המחדל שומר היסטוריה וזיכרון מודל בזיכרון התהליך. להרצה עם כמה אינסטנסים
  או שמירה לאורך זמן — חבר את `REDIS_URL` (Upstash) לפי ההערה בקוד.
