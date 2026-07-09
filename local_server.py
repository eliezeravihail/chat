"""
Local HTTP wrapper around core.py, for the Baileys bridge.

The Baileys Node process (baileys/index.js) logs into WhatsApp with your
(second) number, receives messages, and POSTs them here; this returns the
model's reply. Meant to run on localhost only.

Env vars:
  OPENROUTER_KEY   OpenRouter API key (required, via core)
  REDIS_URL        Upstash redis:// URL (optional; falls back to in-memory)
  LOCAL_TOKEN      Optional shared secret; if set, requests must send it in
                   the X-Token header. Keeps other local processes out.

Run:  uvicorn local_server:app --host 127.0.0.1 --port 8090
"""

from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

import core

LOCAL_TOKEN = os.environ.get("LOCAL_TOKEN", "")

app = FastAPI()


class ReplyIn(BaseModel):
    uid: str
    text: str = ""
    image_data_uri: str | None = None


class ReplyOut(BaseModel):
    reply: str


@app.post("/reply", response_model=ReplyOut)
async def reply(inp: ReplyIn, x_token: str | None = Header(default=None)) -> ReplyOut:
    if LOCAL_TOKEN and x_token != LOCAL_TOKEN:
        raise HTTPException(401, "bad token")
    if inp.image_data_uri:
        text = await core.ask_llm(
            inp.uid, inp.text or "מה רואים בתמונה?", image_data_uri=inp.image_data_uri
        )
    else:
        text = await core.handle_command(inp.uid, inp.text) or await core.ask_llm(
            inp.uid, inp.text
        )
    return ReplyOut(reply=text)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
