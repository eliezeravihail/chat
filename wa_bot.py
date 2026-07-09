"""
Meta WhatsApp Cloud API -> OpenRouter bridge (single authorized user).

Requires a Meta/Facebook Business account. For a setup that needs no Facebook
account, see twilio_bot.py instead — both share core.py.

Env vars:
  WA_TOKEN            Meta permanent access token
  WA_PHONE_ID         Phone number ID from Meta Business
  WA_VERIFY_TOKEN     Arbitrary string; must match what you type in Meta's webhook UI
  WA_APP_SECRET       App secret (for X-Hub-Signature-256 validation)
  ALLOWED_WA_ID       Your own wa_id, e.g. "9725XXXXXXXX"
  OPENROUTER_KEY      OpenRouter API key
  REDIS_URL           Upstash redis:// URL (optional; falls back to in-memory)

Run:  uvicorn wa_bot:app --host 0.0.0.0 --port 8080
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response

import core

WA_TOKEN = os.environ["WA_TOKEN"]
WA_PHONE_ID = os.environ["WA_PHONE_ID"]
WA_VERIFY_TOKEN = os.environ["WA_VERIFY_TOKEN"]
WA_APP_SECRET = os.environ["WA_APP_SECRET"].encode()
ALLOWED_WA_ID = os.environ["ALLOWED_WA_ID"]

GRAPH = f"https://graph.facebook.com/v21.0/{WA_PHONE_ID}/messages"
MAX_MSG_AGE = 300  # ignore messages older than 5 min (webhook backlog replay)

app = FastAPI()


# --- signature ---------------------------------------------------------
def verify_signature(body: bytes, header: str | None) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(WA_APP_SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[7:])


# --- whatsapp send -----------------------------------------------------
async def send_text(wa_id: str, text: str) -> None:
    chunks = core.split_chunks(text) if text else [""]
    async with httpx.AsyncClient(timeout=30) as client:
        for chunk in chunks:
            r = await client.post(
                GRAPH,
                headers={"Authorization": f"Bearer {WA_TOKEN}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": wa_id,
                    "type": "text",
                    "text": {"body": chunk, "preview_url": False},
                },
            )
            if r.status_code >= 400:
                print("WA send failed:", r.status_code, r.text)


async def mark_read_and_typing(message_id: str) -> None:
    """Blue ticks + 'typing…' bubble (lasts up to 25s or until we reply).

    Pure UX sugar — failures are logged and ignored.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(
                GRAPH,
                headers={"Authorization": f"Bearer {WA_TOKEN}"},
                json={
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": message_id,
                    "typing_indicator": {"type": "text"},
                },
            )
        if r.status_code >= 400:
            print("typing indicator failed:", r.status_code, r.text[:200])
    except httpx.HTTPError as exc:
        print("typing indicator failed:", exc)


# --- whatsapp media ----------------------------------------------------
async def download_media(media_id: str) -> tuple[bytes, str]:
    """Fetch a WhatsApp media object; returns (bytes, mime_type).

    Two steps: resolve the media id to a short-lived URL, then download it.
    Both calls require the WA_TOKEN bearer.
    """
    async with httpx.AsyncClient(timeout=60) as client:
        meta = await client.get(
            f"https://graph.facebook.com/v21.0/{media_id}",
            headers={"Authorization": f"Bearer {WA_TOKEN}"},
        )
        meta.raise_for_status()
        info = meta.json()
        mime = info.get("mime_type", "image/jpeg").split(";")[0]
        media = await client.get(
            info["url"], headers={"Authorization": f"Bearer {WA_TOKEN}"}
        )
        media.raise_for_status()
        return media.content, mime


# --- background worker -------------------------------------------------
async def process(wa_id: str, text: str, media_id: str | None = None,
                  message_id: str | None = None) -> None:
    if message_id:
        await mark_read_and_typing(message_id)
    try:
        if media_id:
            data, mime = await download_media(media_id)
            data_uri = f"data:{mime};base64,{base64.b64encode(data).decode()}"
            reply = await core.ask_llm(wa_id, text or "מה רואים בתמונה?", image_data_uri=data_uri)
        else:
            reply = await core.handle_command(wa_id, text) or await core.ask_llm(wa_id, text)
    except Exception as exc:  # noqa: BLE001
        reply = f"⚠️ שגיאה: {exc!r}"
    await send_text(wa_id, reply)


# --- routes ------------------------------------------------------------
@app.get("/webhook")
async def verify(request: Request) -> Response:
    q = request.query_params
    if q.get("hub.mode") == "subscribe" and q.get("hub.verify_token") == WA_VERIFY_TOKEN:
        return Response(content=q.get("hub.challenge", ""), media_type="text/plain")
    raise HTTPException(403, "verification failed")


@app.post("/webhook")
async def webhook(request: Request, bg: BackgroundTasks) -> dict[str, Any]:
    body = await request.body()
    if not verify_signature(body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(403, "bad signature")

    payload = json.loads(body)
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                wa_id = msg.get("from")
                if wa_id != ALLOWED_WA_ID:
                    print("ignored message from", wa_id)
                    continue
                msg_id = msg.get("id", "")
                # Meta delivers at-least-once; a redelivered id must not
                # produce a second reply.
                if msg_id and await core.store.seen(msg_id):
                    print("duplicate delivery skipped:", msg_id)
                    continue
                # After downtime Meta replays its backlog; don't answer stale
                # messages the user sent hours ago.
                ts = int(msg.get("timestamp", "0") or 0)
                if ts and time.time() - ts > MAX_MSG_AGE:
                    print("stale message skipped:", msg_id)
                    continue
                mtype = msg.get("type")
                if mtype == "text":
                    bg.add_task(process, wa_id, msg["text"]["body"], None, msg_id)
                elif mtype == "image":
                    img = msg["image"]
                    bg.add_task(process, wa_id, img.get("caption", ""), img["id"], msg_id)
                else:
                    bg.add_task(send_text, wa_id, "אני תומך כרגע בטקסט ובתמונות בלבד.")

    # Always 200 fast — Meta retries on timeout, which would duplicate replies.
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
