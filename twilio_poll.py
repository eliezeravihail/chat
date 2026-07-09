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
  ALLOWED_WA_ID        your number, e.g. whatsapp:+9725XXXXXXXX
  POLL_SECONDS         optional, default 4

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
    return addr.replace("whatsapp:", "").replace("+", "").strip()


ALLOWED = _norm(os.environ["ALLOWED_WA_ID"])
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "4"))

BASE = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}"
AUTH = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


async def send_text(client: httpx.AsyncClient, text: str) -> None:
    to = f"whatsapp:+{ALLOWED}"
    for chunk in core.split_chunks(text) if text else [""]:
        r = await client.post(
            f"{BASE}/Messages.json",
            auth=AUTH,
            data={"From": TWILIO_FROM, "To": to, "Body": chunk},
        )
        if r.status_code >= 400:
            print("send failed:", r.status_code, r.text[:200])


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
    if not sid or await core.store.seen(sid):
        return
    body = msg.get("body", "") or ""
    image = None
    if int(msg.get("num_media", "0") or 0) > 0:
        image = await fetch_image(client, sid)
    try:
        if image:
            reply = await core.ask_llm(ALLOWED, body or "מה רואים בתמונה?", image_data_uri=image)
        else:
            reply = await core.handle_command(ALLOWED, body) or await core.ask_llm(ALLOWED, body)
    except Exception as exc:  # noqa: BLE001
        reply = f"⚠️ שגיאה: {exc!r}"
    await send_text(client, reply)


async def main() -> None:
    print(f"polling Twilio every {POLL_SECONDS}s — כתוב לבוט מהוואטסאפ שלך. Ctrl-C לעצור.")
    first = True
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            try:
                r = await client.get(
                    f"{BASE}/Messages.json",
                    auth=AUTH,
                    params={"From": f"whatsapp:+{ALLOWED}", "To": TWILIO_FROM, "PageSize": 20},
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
