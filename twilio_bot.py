"""
Twilio WhatsApp -> OpenRouter bridge (single authorized user).

Uses Twilio's WhatsApp API — no Meta/Facebook account required. Works with the
Twilio Sandbox out of the box (send "join <code>" to the sandbox number once),
or a full Twilio WhatsApp sender in production.

Env vars:
  TWILIO_ACCOUNT_SID   Twilio Account SID (starts with "AC…")
  TWILIO_AUTH_TOKEN    Twilio Auth Token (used for REST auth + signature check)
  TWILIO_FROM          Sender, e.g. "whatsapp:+14155238886" (sandbox number)
  ALLOWED_WA_ID        The only number allowed to chat, e.g. "whatsapp:+9725XXXXXXXX"
                       (with or without the "whatsapp:" prefix — normalized below)
  PUBLIC_URL           Public https URL of this service, e.g.
                       "https://myapp.fly.dev" — used to validate Twilio's
                       request signature. Optional but recommended.
  OPENROUTER_KEY       OpenRouter API key
  REDIS_URL            Upstash redis:// URL (optional; falls back to in-memory)

Run:  uvicorn twilio_bot:app --host 0.0.0.0 --port 8080
Point your Twilio WhatsApp "When a message comes in" webhook at:
  https://<host>/webhook   (HTTP POST)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

import httpx
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request

import core

TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_FROM = os.environ["TWILIO_FROM"]
OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]  # validated by core; kept for clarity
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")


def _norm(addr: str) -> str:
    """Normalize a WhatsApp address to bare digits (drop 'whatsapp:' and '+')."""
    return addr.replace("whatsapp:", "").replace("+", "").strip()


ALLOWED_WA_ID = _norm(os.environ["ALLOWED_WA_ID"])

TWILIO_MESSAGES = (
    f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
)

app = FastAPI()


# --- signature ---------------------------------------------------------
def verify_signature(url: str, params: dict[str, str], header: str | None) -> bool:
    """Validate Twilio's X-Twilio-Signature.

    Twilio signs: the exact webhook URL, then each POST field appended as
    key+value in alphabetical key order, HMAC-SHA1 with the auth token, base64.
    """
    if not header:
        return False
    payload = url + "".join(k + params[k] for k in sorted(params))
    digest = hmac.new(
        TWILIO_AUTH_TOKEN.encode(), payload.encode("utf-8"), hashlib.sha1
    ).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, header)


# --- twilio send -------------------------------------------------------
async def send_text(to: str, text: str) -> None:
    to_addr = to if to.startswith("whatsapp:") else f"whatsapp:+{_norm(to)}"
    chunks = core.split_chunks(text) if text else [""]
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    async with httpx.AsyncClient(timeout=30) as client:
        for chunk in chunks:
            r = await client.post(
                TWILIO_MESSAGES,
                auth=auth,
                data={"From": TWILIO_FROM, "To": to_addr, "Body": chunk},
            )
            if r.status_code >= 400:
                print("Twilio send failed:", r.status_code, r.text[:300])


# --- twilio media ------------------------------------------------------
async def download_media(url: str) -> tuple[bytes, str]:
    """Download a Twilio media URL (requires Basic auth); returns (bytes, mime)."""
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        r = await client.get(url, auth=auth)
        r.raise_for_status()
        mime = r.headers.get("content-type", "image/jpeg").split(";")[0]
        return r.content, mime


# --- background worker -------------------------------------------------
async def process(uid: str, text: str, media_url: str | None = None) -> None:
    try:
        if media_url:
            data, mime = await download_media(media_url)
            data_uri = f"data:{mime};base64,{base64.b64encode(data).decode()}"
            reply = await core.ask_llm(uid, text or "מה רואים בתמונה?", image_data_uri=data_uri)
        else:
            reply = await core.handle_command(uid, text) or await core.ask_llm(uid, text)
    except Exception as exc:  # noqa: BLE001
        reply = f"⚠️ שגיאה: {exc!r}"
    await send_text(uid, reply)


# --- routes ------------------------------------------------------------
@app.post("/webhook")
async def webhook(request: Request, bg: BackgroundTasks) -> dict[str, str]:
    form = await request.form()
    params = {k: str(v) for k, v in form.items()}

    # Validate Twilio's signature against the public URL it called.
    url = f"{PUBLIC_URL}/webhook" if PUBLIC_URL else str(request.url)
    if not verify_signature(url, params, request.headers.get("X-Twilio-Signature")):
        raise HTTPException(403, "bad signature")

    sender = _norm(params.get("From", ""))
    if sender != ALLOWED_WA_ID:
        print("ignored message from", sender)
        return {"status": "ignored"}

    # Twilio delivers at-least-once; a redelivered SID must not reply twice.
    msg_sid = params.get("MessageSid", "")
    if msg_sid and await core.store.seen(msg_sid):
        print("duplicate delivery skipped:", msg_sid)
        return {"status": "duplicate"}

    body = params.get("Body", "")
    num_media = int(params.get("NumMedia", "0") or 0)
    if num_media > 0 and params.get("MediaContentType0", "").startswith("image/"):
        bg.add_task(process, sender, body, params.get("MediaUrl0"))
    elif num_media > 0:
        bg.add_task(send_text, sender, "אני תומך כרגע בטקסט ובתמונות בלבד.")
    else:
        bg.add_task(process, sender, body)

    # Empty TwiML — we reply asynchronously via the REST API, not inline.
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
