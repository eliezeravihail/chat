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
_alerted = False  # don't spam ntfy — one alert per limit-hit episode


async def notify(client: httpx.AsyncClient, text: str, high: bool = False) -> None:
    """Push an out-of-band alert to ntfy (works even when WhatsApp is blocked)."""
    if not NTFY_TOPIC:
        return
    try:
        await client.post(
            f"{NTFY_SERVER}/{NTFY_TOPIC}",
            data=text.encode("utf-8"),
            headers={"Title": "בוט Twilio", "Priority": "high" if high else "default"},
        )
    except httpx.HTTPError as exc:
        print("ntfy push failed:", exc)


async def send_text(client: httpx.AsyncClient, to_digits: str, text: str) -> None:
    global _alerted
    to = f"whatsapp:+{to_digits}"
    for chunk in core.split_chunks(text) if text else [""]:
        r = await client.post(
            f"{BASE}/Messages.json",
            auth=AUTH,
            data={"From": TWILIO_FROM, "To": to, "Body": chunk},
        )
        if r.status_code < 400:
            _alerted = False  # a successful send clears the alert latch
            continue
        body = r.text[:300]
        print("send failed:", r.status_code, body, flush=True)
        # Detect the sandbox daily-message limit specifically.
        limit_hit = "63038" in body or "daily messages limit" in body.lower()
        if not _alerted:
            _alerted = True
            if limit_hit:
                await notify(client, "⚠️ הגעת למגבלת 50 ההודעות היומית של Twilio (63038). "
                                     "לא באג — מתאפס בעוד ~24 שעות.", high=True)
            else:
                await notify(client, f"⚠️ שליחת הודעה נכשלה ({r.status_code}). בדוק את הבוט.", high=True)


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
            await send_text(client, num, STARTUP_MESSAGE)
            print("startup message sent to", num)
        except Exception as exc:  # noqa: BLE001
            print("startup message to", num, "failed:", exc)


async def main() -> None:
    print(f"polling Twilio every {POLL_SECONDS}s — מאזין ל: {', '.join(sorted(ALLOWED))}. Ctrl-C לעצור.")
    first = True
    async with httpx.AsyncClient(timeout=30) as client:
        # Startup ping to ntfy — confirms the bot is running AND that the ntfy
        # pipe works, independent of WhatsApp (which may be at its daily limit).
        await notify(client, "🤖 הבוט עלה ורץ (Twilio). מאזין להודעות.")
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
