"""
Platform-neutral core for the chat bridge.

Everything here is independent of the messaging platform (WhatsApp Cloud API,
Twilio, …): model routing, conversation memory, commands, and WhatsApp-style
text formatting. A platform adapter only has to receive a message, call
`ask_llm` / `handle_command`, and send the reply back.

Env vars:
  OPENROUTER_KEY   OpenRouter API key (required)
  REDIS_URL        Upstash redis:// URL (optional; falls back to in-memory)
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict, deque

import httpx

# Load a local .env automatically, so no `source .env` is needed (works the
# same on Windows/macOS/Linux). Every entrypoint imports core first, so this
# runs before any adapter reads its own env vars.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass

OPENROUTER_KEY = os.environ["OPENROUTER_KEY"]
OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS = "https://openrouter.ai/api/v1/models"
REDIS_URL = os.environ.get("REDIS_URL")

# "auto" = use whatever free models are currently available (discovered live
# from OpenRouter). Switch to a premium model any time with /model claude.
DEFAULT_MODEL = "auto"
MODEL_ALIASES = {
    "auto": "auto",                                 # best available free model
    "free": "auto",
    "deepseek": "deepseek/deepseek-chat-v3-0324",   # cheap paid (~cents/month)
    "mini": "openai/gpt-4o-mini",                   # cheap paid
    "hy3": "tencent/hy3",                           # Tencent Hunyuan Hy3
    "gpt": "openai/gpt-4o",                         # premium
    "claude": "anthropic/claude-sonnet-4.5",        # premium
}

# Preferred families, in order, when ranking the discovered free models.
_MODEL_PREF = ["deepseek", "llama", "qwen", "mistral", "gemini", "gemma", "glm", "phi"]

# Last-resort static lists, used only if the live model list can't be fetched.
TEXT_FALLBACKS = [
    "deepseek/deepseek-chat-v3-0324:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
]
VISION_FALLBACKS = [
    "meta-llama/llama-3.2-11b-vision-instruct:free",
    "qwen/qwen-2.5-vl-72b-instruct:free",
]

_free_cache: dict | None = None


async def free_models() -> dict:
    """Discover currently-free models from OpenRouter (cached for the process).

    Free model slugs rot over time, so instead of hardcoding them we read the
    live list and keep the ones priced at 0. Falls back to the static lists if
    the fetch fails.
    """
    global _free_cache
    if _free_cache is not None:
        return _free_cache
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(
                OPENROUTER_MODELS, headers={"Authorization": f"Bearer {OPENROUTER_KEY}"}
            )
            r.raise_for_status()
            data = r.json().get("data", [])
    except Exception as exc:  # noqa: BLE001
        print("free-model discovery failed, using static list:", exc)
        _free_cache = {"text": list(TEXT_FALLBACKS), "vision": list(VISION_FALLBACKS)}
        return _free_cache

    def is_free(m: dict) -> bool:
        p = m.get("pricing", {})
        try:
            return float(p.get("prompt", 1)) == 0 and float(p.get("completion", 1)) == 0
        except (TypeError, ValueError):
            return False

    def rank(mid: str) -> int:
        low = mid.lower()
        for i, fam in enumerate(_MODEL_PREF):
            if fam in low:
                return i
        return len(_MODEL_PREF)

    text, vision = [], []
    for m in data:
        if not is_free(m):
            continue
        mid = m.get("id")
        if not mid:
            continue
        text.append(mid)
        if "image" in (m.get("architecture", {}).get("input_modalities") or []):
            vision.append(mid)
    text.sort(key=rank)
    vision.sort(key=rank)
    _free_cache = {
        "text": text or list(TEXT_FALLBACKS),
        "vision": vision or list(VISION_FALLBACKS),
    }
    print(f"discovered {len(text)} free text models, {len(vision)} free vision models")
    return _free_cache

SYSTEM_PROMPT = (
    "אתה עוזר אישי שמשוחח בוואטסאפ. ענה בשפה שבה המשתמש כותב (ברירת מחדל: עברית), "
    "בטון טבעי וזורם של שיחה, ובתמציתיות — זו הודעת וואטסאפ, לא מסמך. "
    "עיצוב טקסט: וואטסאפ בלבד — *הדגשה* בכוכבית אחת, _הטיה_ בקו תחתון, ```קוד``` בגרשיים משולשים. "
    "אל תשתמש בכותרות Markdown (#), בטבלאות או בהדגשה בכוכבית כפולה. "
    "פסקאות קצרות; רשימות עם • או מספרים. אמוג'י במידה וכשזה מוסיף."
)

SHOW_MODEL = os.environ.get("SHOW_MODEL", "1") != "0"  # append which model replied
WA_MAX_CHARS = 4000            # WhatsApp caps a message at 4096; leave headroom
HISTORY_TURNS = 40             # user+assistant messages retained
HISTORY_TTL = 60 * 60 * 24 * 30  # conversation kept 30 days after last message
SEEN_TTL = 60 * 60            # dedup window for webhook redeliveries


# --- state / persistence ----------------------------------------------
# Chat platforms only deliver the newest message, so conversation memory must
# live here. Two backends implement the same async interface:
#   * RedisStore  — survives restarts / redeploys / machine sleep (Upstash).
#   * MemoryStore — process-local; fine for local dev or a single always-on box.
# History is kept under f"hist:{uid}" (list of role/content dicts, TTL 30d)
# and the selected model under f"model:{uid}".


class MemoryStore:
    def __init__(self) -> None:
        self._history: dict[str, deque] = defaultdict(lambda: deque(maxlen=HISTORY_TURNS))
        self._model: dict[str, str] = {}
        self._seen: deque = deque(maxlen=1000)

    async def get_history(self, uid: str) -> list[dict]:
        return list(self._history[uid])

    async def append(self, uid: str, user_msg: dict, assistant_msg: dict) -> None:
        self._history[uid].append(user_msg)
        self._history[uid].append(assistant_msg)

    async def clear(self, uid: str) -> None:
        self._history[uid].clear()

    async def get_model(self, uid: str) -> str:
        return self._model.get(uid, DEFAULT_MODEL)

    async def set_model(self, uid: str, model: str) -> None:
        self._model[uid] = model

    async def seen(self, msg_id: str) -> bool:
        """True if this message id was already processed (marks it as seen)."""
        if msg_id in self._seen:
            return True
        self._seen.append(msg_id)
        return False


class RedisStore:
    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis  # imported lazily so redis is optional

        self._r = aioredis.from_url(url, decode_responses=True)

    @staticmethod
    def _hist_key(uid: str) -> str:
        return f"hist:{uid}"

    @staticmethod
    def _model_key(uid: str) -> str:
        return f"model:{uid}"

    async def get_history(self, uid: str) -> list[dict]:
        raw = await self._r.get(self._hist_key(uid))
        return json.loads(raw) if raw else []

    async def append(self, uid: str, user_msg: dict, assistant_msg: dict) -> None:
        hist = await self.get_history(uid)
        hist.extend([user_msg, assistant_msg])
        hist = hist[-HISTORY_TURNS:]
        await self._r.set(self._hist_key(uid), json.dumps(hist), ex=HISTORY_TTL)

    async def clear(self, uid: str) -> None:
        await self._r.delete(self._hist_key(uid))

    async def get_model(self, uid: str) -> str:
        return await self._r.get(self._model_key(uid)) or DEFAULT_MODEL

    async def set_model(self, uid: str, model: str) -> None:
        await self._r.set(self._model_key(uid), model)

    async def seen(self, msg_id: str) -> bool:
        """True if this message id was already processed (marks it as seen).

        SET NX is atomic, so concurrent redeliveries can't both pass.
        """
        added = await self._r.set(f"seen:{msg_id}", "1", nx=True, ex=SEEN_TTL)
        return not added


store: MemoryStore | RedisStore = RedisStore(REDIS_URL) if REDIS_URL else MemoryStore()
print("state backend:", type(store).__name__)


# --- formatting ---------------------------------------------------------
_MD_HEADING = re.compile(r"^#{1,6}\s*(.+)$", re.MULTILINE)
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)
_MD_BULLET = re.compile(r"^(\s*)-\s+", re.MULTILINE)


def to_whatsapp(text: str) -> str:
    """Convert common Markdown that LLMs emit into WhatsApp formatting.

    WhatsApp renders *bold*, _italic_ and ```mono``` only; headings, ** and
    tables show up as literal punctuation. The system prompt asks for WhatsApp
    style already — this is the safety net for models that ignore it.
    """
    text = _MD_HEADING.sub(r"*\1*", text)
    text = _MD_BOLD.sub(r"*\1*", text)
    text = _MD_BULLET.sub(r"\1• ", text)
    return text


def split_chunks(text: str, limit: int = WA_MAX_CHARS) -> list[str]:
    """Split long text at paragraph/word boundaries instead of mid-word."""
    chunks: list[str] = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = text.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    chunks.append(text)
    return chunks


# --- llm ---------------------------------------------------------------
MAX_TRIES = 4  # models to try per message, so one bad round stays fast

# Remembers the last free model that actually worked, per user (in-memory).
# On 'auto' we try it first, so we don't re-scan the whole pool every message.
_last_good: dict[str, str] = {}


async def candidate_models(current: str, vision: bool) -> list[str]:
    """Ordered models to try: the user's explicit choice first (if any), then
    the live free pool. On 'auto' it's just the free pool. A model that can't
    handle the request simply errors and the loop moves on."""
    pool = (await free_models())["vision" if vision else "text"]
    if current == "auto":
        return list(pool)
    return [current] + [m for m in pool if m != current]


async def _call_openrouter(model: str, messages: list[dict]) -> tuple[str | None, str]:
    """Single OpenRouter call. Returns (reply, error); reply is None on failure."""
    try:
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(
                OPENROUTER,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "HTTP-Referer": "https://localhost",
                    "X-Title": "wa-bridge",
                },
                json={"model": model, "messages": messages},
            )
    except httpx.HTTPError as exc:
        return None, f"network {exc!r}"
    if r.status_code >= 400:
        return None, f"{r.status_code} {r.text[:200]}"
    try:
        return r.json()["choices"][0]["message"]["content"], ""
    except (KeyError, IndexError, ValueError):
        # OpenRouter sometimes returns an error object with HTTP 200.
        return None, r.text[:200]


async def ask_llm(uid: str, prompt: str, image_data_uri: str | None = None) -> str:
    hist = await store.get_history(uid)
    current = await store.get_model(uid)
    vision = image_data_uri is not None

    # Build the outgoing user message (text, or text + image for vision turns).
    if vision:
        content: list[dict] = []
        if prompt:
            content.append({"type": "text", "text": prompt})
        content.append({"type": "image_url", "image_url": {"url": image_data_uri}})
        user_msg: dict = {"role": "user", "content": content}
        # Don't store the base64 blob in history — keep a light text marker so
        # follow-up turns stay small and the image isn't re-sent every time.
        hist_user_msg = {"role": "user", "content": (prompt + " " if prompt else "") + "[תמונה]"}
    else:
        user_msg = {"role": "user", "content": prompt}
        hist_user_msg = user_msg

    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + hist + [user_msg]

    cands = await candidate_models(current, vision)
    # On 'auto', try the model that worked last time first — so a good pick is
    # reused instead of re-scanning the whole pool on every message.
    if current == "auto" and _last_good.get(uid) in cands:
        lg = _last_good[uid]
        cands = [lg] + [m for m in cands if m != lg]
    cands = cands[:MAX_TRIES]

    for model in cands:
        reply, err = await _call_openrouter(model, messages)
        if reply is None:
            print("model failed:", model, err[:100])
            continue

        if current == "auto":
            _last_good[uid] = model
        # On an explicit choice, note a per-turn fallback; on 'auto' any free
        # model is expected, so stay quiet.
        note = ""
        if current != "auto" and model != current:
            note = f"ℹ️ {current} לא זמין כרגע — עניתי עם {model}.\n\n"
        # Persist only on success, so a failed turn doesn't poison the context.
        await store.append(uid, hist_user_msg, {"role": "assistant", "content": reply})
        tag = f"\n\n_— {model}_" if SHOW_MODEL else ""
        return note + to_whatsapp(reply) + tag

    if vision:
        return "⚠️ אף מודל ראייה חינמי זמין כרגע. נסה שוב מאוחר יותר, או /model claude."
    return (
        "⚠️ המודלים החינמיים עמוסים כרגע (rate limit).\n"
        "אפשרויות: נסה שוב בעוד רגע · /model deepseek (זול מאוד) · "
        "או הוסף קצת קרדיט ב-OpenRouter כדי להעלות את המגבלה של המודלים החינמיים."
    )


# --- commands ----------------------------------------------------------
async def handle_command(uid: str, text: str) -> str | None:
    if not text.startswith("/"):
        return None
    cmd, _, arg = text[1:].partition(" ")
    cmd, arg = cmd.lower(), arg.strip()

    if cmd == "clear":
        await store.clear(uid)
        return "🧹 ההקשר נוקה."
    if cmd == "models":
        current = await store.get_model(uid)
        aliases = ", ".join(MODEL_ALIASES)
        free = (await free_models())["text"][:8]
        free_list = "\n".join(f"• {m}" for m in free) or "(לא נמצאו כרגע)"
        return (
            f"מודל נוכחי: {current}\n\n"
            f"קיצורים: {aliases}\n"
            "(`/model auto` = הכי טוב חינמי, `/model claude` = בתשלום)\n\n"
            "מודלים חינמיים זמינים כרגע:\n" + free_list +
            "\n\n📷 שליחת תמונה עוברת אוטומטית למודל ראייה חינמי."
        )
    if cmd == "model":
        if not arg:
            current = await store.get_model(uid)
            return f"מודל נוכחי: {current}"
        model = MODEL_ALIASES.get(arg, arg)
        await store.set_model(uid, model)
        await store.clear(uid)
        return f"✅ הוחלף ל־{model} (ההקשר אופס)."
    return "פקודה לא מוכרת. נסה /models, /model <שם>, /clear"
