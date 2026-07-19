"""
Chat with the bot over an ntfy topic — RECEIVES and SENDS (bidirectional).

Lets you talk to the bot from a plain browser at
``https://<NTFY_SERVER>/<NTFY_CHAT_TOPIC>`` — no app install, no WhatsApp, no
Facebook, no Twilio 50/day limit. You type in the topic's message box; the bot
reads the stream, answers, and publishes the reply back to the same topic so it
shows up on the page.

It's just another channel adapter on top of the platform-neutral core: it
receives a message, calls ``core.respond()``, and delivers the reply — the same
seam the Twilio adapter uses. Adding Telegram later is the same shape.

Security: the topic name is the ONLY secret — anyone who knows it can chat (and
spend your OpenRouter credit). Pick an unguessable name (treat it like a
password), e.g. ``moshe-9f3kd21x``. For stronger isolation, self-host ntfy.

Env (.env, loaded automatically via core):
  OPENROUTER_KEY      required (read by core)
  NTFY_CHAT_TOPIC     the chat topic — REQUIRED (unguessable = your password).
                      Falls back to NTFY_TOPIC if set.
  NTFY_SERVER         optional, default https://ntfy.sh
  NTFY_UID            conversation id for memory/model, default "ntfy"
  NTFY_GREETING       optional greeting published on startup ("" = none)

Run:  python ntfy_channel.py
Chat: open https://ntfy.sh/<NTFY_CHAT_TOPIC> in a browser and type.
"""

from __future__ import annotations

import asyncio
import json
import os

import httpx

import core  # loads .env, exposes respond() / split_chunks

NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
NTFY_CHAT_TOPIC = os.environ.get("NTFY_CHAT_TOPIC") or os.environ.get("NTFY_TOPIC", "")
NTFY_UID = os.environ.get("NTFY_UID", "ntfy")
NTFY_GREETING = os.environ.get("NTFY_GREETING", "משה מחובר ומקשיב 🌿")

# ntfy HTTP headers must be ASCII, so this marker title is ASCII. The bot tags
# every reply with it and skips any incoming stream message that carries it —
# that's how it avoids answering its own messages on the shared topic.
BOT_TITLE = "Moshe"

if not NTFY_CHAT_TOPIC:
    raise SystemExit(
        "Set NTFY_CHAT_TOPIC to an unguessable topic name (it acts as the password)."
    )


async def publish(client: httpx.AsyncClient, text: str) -> None:
    """Publish a reply to the chat topic (chunked to stay under limits)."""
    for chunk in core.split_chunks(text) if text else [""]:
        try:
            await client.post(
                f"{NTFY_SERVER}/{NTFY_CHAT_TOPIC}",
                content=chunk.encode("utf-8"),
                headers={"Title": BOT_TITLE, "Markdown": "yes"},
                timeout=20,
            )
        except Exception as exc:  # noqa: BLE001 — a failed publish shouldn't kill the loop
            print("ntfy publish failed:", exc, flush=True)


async def handle(client: httpx.AsyncClient, msg: dict) -> None:
    text = (msg.get("message") or "").strip()
    if not text:
        return
    reply = await core.respond(NTFY_UID, text)  # channel-neutral core call
    await publish(client, reply)


async def main() -> None:
    url = f"{NTFY_SERVER}/{NTFY_CHAT_TOPIC}/json"
    print(f"ntfy channel up — listening on {url}", flush=True)
    print(f"chat in a browser at {NTFY_SERVER}/{NTFY_CHAT_TOPIC}", flush=True)
    seen: set[str] = set()  # dedup message ids across reconnects
    # timeout=None: the subscribe stream is long-lived (keepalives arrive ~30s).
    async with httpx.AsyncClient(timeout=None) as client:
        if NTFY_GREETING:
            await publish(client, NTFY_GREETING)
        while True:
            try:
                async with client.stream("GET", url) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            msg = json.loads(line)
                        except ValueError:
                            continue
                        if msg.get("event") != "message":
                            continue  # skip open/keepalive/poll_request events
                        if msg.get("title") == BOT_TITLE:
                            continue  # our own reply — don't answer ourselves
                        mid = msg.get("id")
                        if mid:
                            if mid in seen:
                                continue
                            seen.add(mid)
                            if len(seen) > 2000:
                                seen.pop()
                        await handle(client, msg)
            except Exception as exc:  # noqa: BLE001 — reconnect on any stream drop
                print("ntfy stream error — reconnecting in 3s:", exc, flush=True)
                await asyncio.sleep(3)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nbye")
