#!/usr/bin/env python3
"""Ensure the Hermes config is correct for a shared, multi-user WhatsApp bot.

Two things, both idempotent and non-destructive:

1. PRIVACY — ``agent.disabled_toolsets`` disables the toolsets that can leak one
   user's data into another user's chat:
     - ``session_search`` — searches / recalls across ALL stored sessions with
       NO per-user filter (even across profiles). On a multi-user bot this lets
       the model surface another person's conversation when asked "what do you
       know about me". Per-user session isolation does NOT stop this, because the
       tool reads the raw session store directly.
     - ``memory`` — persistent "personal notes + user profile" memory. Same risk.
   ``agent.disabled_toolsets`` is a global denylist that wins over every
   per-platform allowlist. This does NOT remove conversation continuity — the
   ongoing transcript is part of the session, not the ``memory`` toolset.

2. GROUPS — the built-in WhatsApp ``group_policy`` defaults to "pairing", which
   makes the bot IGNORE group messages until a group is approved (that is why it
   stays silent in a group). We set it to "open" so groups are processed, keep
   ``require_mention`` on so the bot replies only when addressed (native
   @mention, a reply to it, or the name pattern), and add "אהרון" as a name
   pattern. Only defaults are filled in — an existing explicit value (e.g. a
   later switch to "allowlist") is respected, never overwritten.

Usage:
    python ensure-private-config.py /path/to/config.yaml

Safe by design: on any error (PyYAML missing, unparseable file, write failure)
it prints a note and exits 0 without changing anything, so it can never break a
running bot's config.
"""
import sys

# Toolsets that must never be active on a shared, multi-user bot. The first two
# are the privacy-critical ones; the rest are heavy/irrelevant and kept off too.
DISABLE = ["session_search", "memory", "browser", "spotify", "web"]

# The bot's name — added to WhatsApp mention patterns so it responds in a group
# when addressed by name, not only when @mentioned.
BOT_NAME = "אהרון"


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: ensure-private-config.py <config.yaml>")
        return 0
    path = sys.argv[1]

    try:
        import yaml
    except Exception:
        print("PyYAML unavailable — skipping privacy-config enforcement")
        return 0

    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        data = {}
    except Exception as exc:  # unparseable → do not touch it
        print(f"could not parse {path} ({exc}) — skipping")
        return 0

    if not isinstance(data, dict):
        print("config root is not a mapping — skipping")
        return 0

    changed = False

    # --- 1. privacy denylist -------------------------------------------------
    agent = data.get("agent")
    if not isinstance(agent, dict):
        agent = {}
    disabled = agent.get("disabled_toolsets")
    if not isinstance(disabled, list):
        disabled = []
    for name in DISABLE:
        if name not in disabled:
            disabled.append(name)
            changed = True
    agent["disabled_toolsets"] = disabled
    data["agent"] = agent

    # --- 2. WhatsApp group settings — REMOVE the group-response keys.
    # `group_policy: open` makes Hermes REFUSE TO START unless WHATSAPP_ALLOW_ALL_USERS
    # is enabled (which would answer everyone — unsafe). That crash-loops the gateway
    # and takes the whole bot offline. So strip the keys we previously set here, back
    # to stock, so the gateway starts and DMs work. Group responses, if wanted, need
    # `group_policy: allowlist` + a specific group JID — never 'open'.
    wa = data.get("whatsapp")
    if isinstance(wa, dict):
        for k in ("group_policy", "require_mention", "mention_patterns"):
            if k in wa:
                del wa[k]
                changed = True
        if wa:
            data["whatsapp"] = wa
        elif "whatsapp" in data:
            del data["whatsapp"]
            changed = True

    if not changed:
        print(f"config already correct — disabled_toolsets = {disabled}; no whatsapp group keys")
        return 0

    try:
        with open(path, "w") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    except Exception as exc:
        print(f"could not write {path} ({exc}) — skipping")
        return 0

    print(
        f"config updated — disabled_toolsets = {disabled}; "
        f"removed whatsapp group_policy/require_mention/mention_patterns (was breaking gateway startup)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
