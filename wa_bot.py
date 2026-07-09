"""
WhatsApp -> OpenRouter bridge (single authorized user).

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

import hashlib
import hmac
import json
import os
from collections import defaultdict, deque
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response

WA_TOKEN = os.environ["WA_TOKEN"]
WA_PHONE_ID = os.environ["WA_PHONE_ID"]
WA_VERIFY_TOKEN = os.environ["WA_VERIFY_TOKEN"]
WA_APP_SECRET = os.environ["WA_APP_SECRET"].encode()
ALLOWED_WA_ID = os.environ["ALLOWED_WA_ID"]
OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]

GRAPH = f"https://graph.facebook.com/v21.0/{WA_PHONE_ID}/messages"
OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_MODEL = "deepseek/deepseek-chat-v3-0324:free"
MODEL_ALIASES = {
    "claude": "anthropic/claude-sonnet-4.5",
    "gpt": "openai/gpt-4o",
    "gemini": "google/gemini-2.0-flash-exp:free",
    "deepseek": "deepseek/deepseek-chat-v3-0324:free",
    "llama": "meta-llama/llama-3.3-70b-instruct:free",
    "qwen": "qwen/qwen-2.5-72b-instruct:free",
}

WA_MAX_CHARS = 4000  # actual cap is 4096; leave headroom
HISTORY_TURNS = 12   # user+assistant messages retained

app = FastAPI()

# --- state -------------------------------------------------------------
# Swap for Upstash Redis in production: history under key f"hist:{wa_id}" (TTL 24h),
# model under f"model:{wa_id}". In-memory is fine for a single user on one instance.
_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=HISTORY_TURNS))
_model: dict[str, str] = defaultdict(lambda: DEFAULT_MODEL)


# --- signature ---------------------------------------------------------
def verify_signature(body: bytes, header: str | None) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(WA_APP_SECRET, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[7:])


# --- whatsapp send -----------------------------------------------------
async def send_text(wa_id: str, text: str) -> None:
    chunks = [text[i:i + WA_MAX_CHARS] for i in range(0, len(text), WA_MAX_CHARS)] or [""]
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


# --- llm ---------------------------------------------------------------
async def ask_llm(wa_id: str, prompt: str) -> str:
    hist = _history[wa_id]
    messages = list(hist) + [{"role": "user", "content": prompt}]

    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            OPENROUTER,
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "HTTP-Referer": "https://localhost",
                "X-Title": "wa-bridge",
            },
            json={"model": _model[wa_id], "messages": messages},
        )
    if r.status_code >= 400:
        return f"⚠️ שגיאת מודל ({r.status_code}): {r.text[:300]}"

    data = r.json()
    try:
        reply = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return f"⚠️ תשובה לא צפויה: {json.dumps(data)[:300]}"

    hist.append({"role": "user", "content": prompt})
    hist.append({"role": "assistant", "content": reply})
    return reply


# --- commands ----------------------------------------------------------
def handle_command(wa_id: str, text: str) -> str | None:
    if not text.startswith("/"):
        return None
    cmd, _, arg = text[1:].partition(" ")
    cmd, arg = cmd.lower(), arg.strip()

    if cmd == "clear":
        _history[wa_id].clear()
        return "🧹 ההקשר נוקה."
    if cmd == "models":
        lines = [f"• {k} → {v}" for k, v in MODEL_ALIASES.items()]
        return "מודלים זמינים:\n" + "\n".join(lines) + f"\n\nנוכחי: {_model[wa_id]}"
    if cmd == "model":
        if not arg:
            return f"מודל נוכחי: {_model[wa_id]}"
        _model[wa_id] = MODEL_ALIASES.get(arg, arg)
        _history[wa_id].clear()
        return f"✅ הוחלף ל־{_model[wa_id]} (ההקשר אופס)."
    return "פקודה לא מוכרת. נסה /models, /model <שם>, /clear"


# --- background worker -------------------------------------------------
async def process(wa_id: str, text: str) -> None:
    try:
        reply = handle_command(wa_id, text) or await ask_llm(wa_id, text)
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
                if msg.get("type") != "text":
                    bg.add_task(send_text, wa_id, "אני תומך כרגע רק בטקסט.")
                    continue
                bg.add_task(process, wa_id, msg["text"]["body"])

    # Always 200 fast — Meta retries on timeout, which would duplicate replies.
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
