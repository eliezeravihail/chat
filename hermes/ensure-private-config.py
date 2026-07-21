#!/usr/bin/env python3
"""Ensure the Hermes config enforces cross-user privacy on a shared bot.

Idempotently guarantees that ``agent.disabled_toolsets`` disables the toolsets
that can leak one user's data into another user's chat:

  - ``session_search`` — searches / recalls across ALL stored sessions with NO
    per-user filter (even across profiles). On a multi-user bot this lets the
    model surface another person's conversation when asked "what do you know
    about me". Per-user session isolation does NOT stop this, because the tool
    reads the raw session store directly.
  - ``memory`` — persistent "personal notes + user profile" memory. Same risk.

``agent.disabled_toolsets`` is a global denylist that wins over every per-platform
allowlist, so listing a toolset here forces it off on every channel.

Note: this does NOT remove conversation continuity — the ongoing chat transcript
is part of the session, not the ``memory`` toolset, and stays intact.

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

    agent = data.get("agent")
    if not isinstance(agent, dict):
        agent = {}
    disabled = agent.get("disabled_toolsets")
    if not isinstance(disabled, list):
        disabled = []

    changed = False
    for name in DISABLE:
        if name not in disabled:
            disabled.append(name)
            changed = True
    agent["disabled_toolsets"] = disabled
    data["agent"] = agent

    if not changed:
        print(f"privacy already enforced — disabled_toolsets = {disabled}")
        return 0

    try:
        with open(path, "w") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    except Exception as exc:
        print(f"could not write {path} ({exc}) — skipping")
        return 0

    print(f"enforced privacy — disabled_toolsets = {disabled}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
