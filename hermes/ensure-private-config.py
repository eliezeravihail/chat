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

    # --- 2. WhatsApp group responses (fill defaults, respect explicit values) -
    wa = data.get("whatsapp")
    if not isinstance(wa, dict):
        wa = {}
    if "group_policy" not in wa:            # default "pairing" ignores groups
        wa["group_policy"] = "open"
        changed = True
    if "require_mention" not in wa:         # only answer when addressed
        wa["require_mention"] = True
        changed = True
    patterns = wa.get("mention_patterns")
    if not isinstance(patterns, list):
        patterns = []
    if BOT_NAME not in patterns:            # let owner address it by name
        patterns.append(BOT_NAME)
        changed = True
    wa["mention_patterns"] = patterns
    data["whatsapp"] = wa

    if not changed:
        print(
            f"config already correct — disabled_toolsets = {disabled}; "
            f"whatsapp.group_policy = {wa['group_policy']}"
        )
        return 0

    try:
        with open(path, "w") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    except Exception as exc:
        print(f"could not write {path} ({exc}) — skipping")
        return 0

    print(
        f"config updated — disabled_toolsets = {disabled}; "
        f"whatsapp.group_policy = {wa['group_policy']}, "
        f"require_mention = {wa['require_mention']}, "
        f"mention_patterns = {patterns}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
