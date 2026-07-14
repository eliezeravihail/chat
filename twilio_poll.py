"""
Twilio WhatsApp bot via POLLING — no public webhook, no ngrok, no server.

Instead of Twilio calling your machine (which needs a public URL), this script
asks Twilio every few seconds "any new messages?" and replies. A little slower
than the webhook, but needs nothing exposed to the internet — just run it.

Env (.env, loaded automatically):
  OPENROUTER_KEY       OpenRouter API key
  TWILIO_ACCOUNT_SID   Twilio Account SID (AC…)
  TWILIO_AUTH_TOKEN    Twilio Auth Token
  TWILIO_FROM          sandbox number, e.g. whatsapp:+14155238886
  ALLOWED_WA_ID        allowed number(s), comma-separated for more than one,
                       e.g. whatsapp:+9725XXXXXXXX,whatsapp:+9725YYYYYYYY
  STARTUP_MESSAGE      optional greeting sent to each allowed number on start
                       (empty = don't send)
  POLL_SECONDS         optional, default 4
  NTFY_TOPIC           optional — if a Twilio SEND fails (e.g. the 50/day
                       sandbox limit, error 63038), push an alert to
                       https://<NTFY_SERVER>/<NTFY_TOPIC>. Empty = no alerts.
  NTFY_SERVER          optional, default https://ntfy.sh
  HEARTBEAT_HOURS      optional, default 6 — every N hours push a heartbeat to
                       ntfy WITH today's Twilio message count/errors (read via
                       the API, which works even when sending is blocked). If
                       this stops arriving, the bot/VM is down. 0 = disabled.

Run:  python twilio_poll.py
"""

from __future__ import annotations

import asyncio
import base64
import os

import httpx

import core  # loads .env and exposes ask_llm / handle_command / store

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_FROM = os.environ["TWILIO_FROM"]


def _norm(addr: str) -> str:
    # keep digits only, so dashes/spaces/() in a pasted number don't break matching
    return "".join(ch for ch in addr if ch.isdigit())


# One or more allowed numbers (comma-separated). The bot ignores everyone else.
ALLOWED = {_norm(a) for a in os.environ["ALLOWED_WA_ID"].split(",") if a.strip()}
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "4"))
STARTUP_MESSAGE = os.environ.get(
    "STARTUP_MESSAGE",
    "🤖 הבוט מחובר ומוכן! פשוט כתוב לי הודעה ואענה. שלח /models לרשימת המודלים.",
)

BASE = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}"
AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
HEARTBEAT_HOURS = float(os.environ.get("HEARTBEAT_HOURS", "6"))


async def notify(client: httpx.AsyncClient, text: str, high: bool = False) -> None:
    """Push an out-of-band alert to ntfy (works even when WhatsApp is blocked)."""
    if not NTFY_TOPIC:
        return
    try:
        # ntfy title/tags travel in HTTP headers, which must be ASCII. Keep the
        # Hebrew in the body (UTF-8); use an ASCII title + the markdown flag so
        # the emoji/Hebrew body renders. (Hebrew in a header crashes httpx.)
        await client.post(
            f"{NTFY_SERVER}/{NTFY_TOPIC}",
            content=text.encode("utf-8"),
            headers={
                "Title": "WhatsApp bot",
                "Priority": "high" if high else "default",
                "Markdown": "yes",
            },
        )
    except Exception as exc:  # noqa: BLE001 — never let a notification crash the bot
        print("ntfy push failed:", exc)


async def send_text(
    client: httpx.AsyncClient, to_digits: str, text: str, alert: bool = True
) -> None:
    """Send a WhatsApp reply via Twilio. If a send fails and alert=True, push an
    ntfy alert EVERY time (no latch) — so each attempt tells you the state.
    Startup/greeting sends pass alert=False to avoid noise."""
    to = f"whatsapp:+{to_digits}"
    for chunk in core.split_chunks(text) if text else [""]:
        r = await client.post(
            f"{BASE}/Messages.json",
            auth=AUTH,
            data={"From": TWILIO_FROM, "To": to, "Body": chunk},
        )
        if r.status_code < 400:
            continue
        body = r.text[:300]
        print("send failed:", r.status_code, body, flush=True)
        if alert:
            if "63038" in body or "daily messages limit" in body.lower():
                await notify(client, "⚠️ ניסית לשלוח — הבוט לא הצליח להשיב: מגבלת 50 ההודעות "
                                     "(63038, חלון נע של 24ש'). הקיבולת מתפנה בהדרגה.", high=True)
            else:
                await notify(client, f"⚠️ ניסית לשלוח — התשובה נכשלה ({r.status_code}).", high=True)
        return  # one alert per message, then stop (further chunks would fail too)


async def fetch_image(client: httpx.AsyncClient, sid: str) -> str | None:
    """Best-effort: return a data URI for the message's first image, or None."""
    try:
        r = await client.get(f"{BASE}/Messages/{sid}/Media.json", auth=AUTH)
        r.raise_for_status()
        media = r.json().get("media_list", [])
        img = next((m for m in media if m.get("content_type", "").startswith("image/")), None)
        if not img:
            return None
        mime = img["content_type"].split(";")[0]
        content = await client.get(
            f"{BASE}/Messages/{sid}/Media/{img['sid']}", auth=AUTH, follow_redirects=True
        )
        content.raise_for_status()
        return f"data:{mime};base64,{base64.b64encode(content.content).decode()}"
    except Exception as exc:  # noqa: BLE001
        print("media fetch failed:", exc)
        return None


async def handle(client: httpx.AsyncClient, msg: dict) -> None:
    sid = msg.get("sid", "")
    sender = _norm(msg.get("from", ""))
    if not sid or sender not in ALLOWED or await core.store.seen(sid):
        return
    body = msg.get("body", "") or ""
    image = None
    if int(msg.get("num_media", "0") or 0) > 0:
        image = await fetch_image(client, sid)
    try:
        # uid = sender, so each allowed number keeps its own history and model.
        if image:
            reply = await core.ask_llm(sender, body or "מה רואים בתמונה?", image_data_uri=image)
        else:
            reply = await core.handle_command(sender, body) or await core.ask_llm(sender, body)
    except Exception as exc:  # noqa: BLE001
        reply = f"⚠️ שגיאה: {exc!r}"
    await send_text(client, sender, reply)


async def announce(client: httpx.AsyncClient) -> None:
    """Greet each allowed number so they know the bot is live and can reply.

    May fail if a number is outside WhatsApp's 24h window (hasn't messaged
    recently) — that's fine, it's logged and ignored.
    """
    if not STARTUP_MESSAGE:
        return
    for num in ALLOWED:
        try:
            await send_text(client, num, STARTUP_MESSAGE, alert=False)
            print("startup message sent to", num)
        except Exception as exc:  # noqa: BLE001
            print("startup message to", num, "failed:", exc)


async def twilio_status(client: httpx.AsyncClient) -> str:
    """Read Twilio activity for the last 24h via the API (works even when
    SENDING is blocked). The sandbox limit is a *rolling* 24h window of 50
    SUCCESSFUL sends — not a calendar-day reset — so we count the rolling
    window and split successful sends from failures (a failed 63038 attempt is
    still an outbound record, so counting raw outbound would exceed 50 and
    look nonsensical). Returns a short Hebrew summary."""
    import datetime
    from email.utils import parsedate_to_datetime

    now = datetime.datetime.now(datetime.timezone.utc)
    window_start = now - datetime.timedelta(hours=24)
    try:
        r = await client.get(f"{BASE}/Messages.json", auth=AUTH, params={"PageSize": 400})
        r.raise_for_status()
        msgs = r.json().get("messages", [])
    except Exception as exc:  # noqa: BLE001
        return f"לא הצלחתי לקרוא מ-Twilio: {exc!r}"

    inbound = sent_ok = failed = 0
    limit_hit = False
    oldest_ok = None  # timestamp of the oldest SUCCESSFUL send still in the window
    for m in msgs:
        raw = m.get("date_created") or m.get("date_sent")
        try:
            ts = parsedate_to_datetime(raw).astimezone(datetime.timezone.utc)
        except (TypeError, ValueError):
            continue
        if ts < window_start:
            continue
        if m.get("direction", "").startswith("inbound"):
            inbound += 1
            continue
        # outbound: separate real sends from failed attempts
        code = str(m.get("error_code") or "")
        status = m.get("status", "")
        if code == "63038":
            limit_hit = True
            failed += 1
        elif code or status in ("failed", "undelivered"):
            failed += 1
        else:
            sent_ok += 1
            if oldest_ok is None or ts < oldest_ok:
                oldest_ok = ts

    line = f"📊 24 שעות אחרונות: {inbound} התקבלו · {sent_ok} נשלחו (מגבלה: 50 בחלון נע)"
    if failed:
        line += f" · {failed} נכשלו"
    if limit_hit or sent_ok >= 50:
        msg = "\n⚠️ מגבלת 50 בחלון נע של 24ש' פעילה — הקיבולת מתפנה בהדרגה"
        if oldest_ok is not None and sent_ok >= 50:
            frees_in_h = ((oldest_ok + datetime.timedelta(hours=24)) - now).total_seconds() / 3600
            if frees_in_h > 0:
                msg += f", מקום נוסף מתפנה בעוד ~{frees_in_h:.0f}ש'"
        line += msg + "."
    return line


async def heartbeat_loop(client: httpx.AsyncClient) -> None:
    """Every HEARTBEAT_HOURS, push a liveness + Twilio-status ping to ntfy.
    If these stop arriving, the bot or VM is down."""
    if HEARTBEAT_HOURS <= 0:
        return
    while True:
        await asyncio.sleep(HEARTBEAT_HOURS * 3600)
        status = await twilio_status(client)
        await notify(client, f"💓 הבוט פעיל.\n{status}")


async def main() -> None:
    print(f"polling Twilio every {POLL_SECONDS}s — מאזין ל: {', '.join(sorted(ALLOWED))}. Ctrl-C לעצור.")
    first = True
    async with httpx.AsyncClient(timeout=30) as client:
        # Startup ping to ntfy — confirms the bot is running AND that the ntfy
        # pipe works, independent of WhatsApp (which may be at its daily limit).
        startup = await twilio_status(client)
        await notify(client, f"🤖 הבוט עלה ורץ (Twilio).\n{startup}")
        asyncio.create_task(heartbeat_loop(client))
        await announce(client)
        while True:
            try:
                r = await client.get(
                    f"{BASE}/Messages.json",
                    auth=AUTH,
                    params={"To": TWILIO_FROM, "PageSize": 20},
                )
                r.raise_for_status()
                msgs = r.json().get("messages", [])
                # Oldest first so replies keep chat order.
                for msg in reversed(msgs):
                    if msg.get("direction") != "inbound":
                        continue
                    if first:
                        # On startup, mark existing messages as seen so we don't
                        # answer old history — only reply to what arrives next.
                        await core.store.seen(msg.get("sid", ""))
                    else:
                        await handle(client, msg)
                first = False
            except Exception as exc:  # noqa: BLE001
                print("poll error:", exc)
            await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
