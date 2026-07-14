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
    """Return (human summary, alert?) for Twilio activity in the last 24h.

    The sandbox limit is a *rolling* 24h window of SANDBOX_LIMIT successful
    sends, not a calendar-day reset. A failed 63038 attempt is still an
    outbound record, so we split successful sends from failures — otherwise
    the "sent" count exceeds the limit and looks nonsensical.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    window_start = now - datetime.timedelta(hours=24)
    with httpx.Client(timeout=30) as client:
        r = client.get(MESSAGES, auth=(SID, TOKEN), params={"PageSize": 400})
        r.raise_for_status()
        msgs = r.json().get("messages", [])

    sent_ok = inbound = failed = 0
    errors: dict[str, int] = {}
    limit_hit = False
    for m in msgs:
        raw = m.get("date_created") or m.get("date_sent")
        if not raw:
            continue
        try:
            if parsedate_to_datetime(raw).astimezone(datetime.timezone.utc) < window_start:
                continue
        except (TypeError, ValueError):
            continue
        if m.get("direction", "").startswith("inbound"):
            inbound += 1
            continue
        code = m.get("error_code")
        status = m.get("status", "")
        if code:
            errors[str(code)] = errors.get(str(code), 0) + 1
            if str(code) == "63038":
                limit_hit = True
        if code or status in ("failed", "undelivered"):
            failed += 1
        else:
            sent_ok += 1

    lines = [
        f"📊 Twilio ב-24ש' אחרונות: {sent_ok} נשלחו · {inbound} נכנסו "
        f"(מגבלה: {SANDBOX_LIMIT} בחלון נע)"
    ]
    if failed:
        lines[0] += f" · {failed} נכשלו"
    if errors:
        lines.append("שגיאות: " + ", ".join(f"{c}×{n}" for c, n in errors.items()))
    alert = False
    if limit_hit or sent_ok >= SANDBOX_LIMIT:
        lines.append(
            "⚠️ מגבלת 50 בחלון נע של 24ש' פעילה (63038) — לא באג. "
            "הקיבולת מתפנה בהדרגה ככל שהודעות ישנות עוברות את גיל 24ש'."
        )
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
