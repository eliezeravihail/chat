"""
Check Twilio message activity for today and push a status update to ntfy.

Answers "is the bot silent because of the 50/day sandbox limit or a bug?"
without opening the Twilio console: it counts today's messages, flags any
error codes (especially 63038 = daily limit), and sends a one-line summary
to your phone via ntfy — which works even when WhatsApp sending is blocked.

Env (reads ~/chat/.env automatically):
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN   (already set for the bot)
  NTFY_TOPIC       a topic name, e.g. "eli-bot-7hK2p" (pick something unguessable)
  NTFY_SERVER      default https://ntfy.sh
  SANDBOX_LIMIT    default 50

Run:  ./.venv/bin/python monitor-twilio.py
Cron (hourly):  0 * * * * cd ~/chat && ./.venv/bin/python monitor-twilio.py
View on phone:  open https://ntfy.sh/<your-topic> in a browser (no app needed).
"""

from __future__ import annotations

import datetime
import os
from email.utils import parsedate_to_datetime

import httpx

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass

SID = os.environ["TWILIO_ACCOUNT_SID"]
TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
SANDBOX_LIMIT = int(os.environ.get("SANDBOX_LIMIT", "50"))

MESSAGES = f"https://api.twilio.com/2010-04-01/Accounts/{SID}/Messages.json"


def summarize() -> tuple[str, bool]:
    """Return (human summary, alert?) for today's Twilio messages."""
    today = datetime.datetime.now(datetime.timezone.utc).date()
    with httpx.Client(timeout=30) as client:
        r = client.get(MESSAGES, auth=(SID, TOKEN), params={"PageSize": 400})
        r.raise_for_status()
        msgs = r.json().get("messages", [])

    out = inbound = 0
    errors: dict[str, int] = {}
    limit_hit = False
    for m in msgs:
        raw = m.get("date_created") or m.get("date_sent")
        if not raw:
            continue
        try:
            if parsedate_to_datetime(raw).astimezone(datetime.timezone.utc).date() != today:
                continue
        except (TypeError, ValueError):
            continue
        if m.get("direction", "").startswith("inbound"):
            inbound += 1
        else:
            out += 1
        code = m.get("error_code")
        if code:
            errors[str(code)] = errors.get(str(code), 0) + 1
            if str(code) == "63038":
                limit_hit = True

    lines = [f"📊 Twilio היום: {out} יצא · {inbound} נכנס (מתוך {SANDBOX_LIMIT}/יום)"]
    if errors:
        lines.append("שגיאות: " + ", ".join(f"{c}×{n}" for c, n in errors.items()))
    alert = False
    if limit_hit:
        lines.append("⚠️ הגעת למגבלת 50 ההודעות היומית (63038) — לא באג. מתאפס בעוד ~24ש'.")
        alert = True
    elif out >= SANDBOX_LIMIT:
        lines.append("⚠️ קרוב/הגעת למגבלה היומית.")
        alert = True
    elif errors:
        lines.append("⚠️ יש שגיאות שליחה — בדוק.")
        alert = True
    return "\n".join(lines), alert


def push(text: str, alert: bool) -> None:
    if not NTFY_TOPIC:
        print("(NTFY_TOPIC not set — printing only)")
        return
    try:
        httpx.post(
            f"{NTFY_SERVER}/{NTFY_TOPIC}",
            data=text.encode("utf-8"),
            headers={
                "Title": "מצב בוט Twilio",
                "Priority": "high" if alert else "default",
                "Tags": "warning" if alert else "bar_chart",
            },
            timeout=15,
        )
    except httpx.HTTPError as exc:
        print("ntfy push failed:", exc)


if __name__ == "__main__":
    summary, alert = summarize()
    print(summary)
    push(summary, alert)
