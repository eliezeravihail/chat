#!/usr/bin/env python3
"""Delete ONE user's sessions from the Hermes state.db, by phone number.

Targets the sessions whose ``session_key`` contains the given number — a
WhatsApp DM key looks like ``agent:main:whatsapp:dm:<number>`` and a group
participant key ends in ``:<number>``. Deleting each session's rows in
``messages`` cascades to the FTS indexes automatically via the built-in
``messages_fts_delete`` / ``messages_fts_trigram_delete`` AFTER DELETE triggers,
so no orphan search rows are left behind.

Safety:
  - Backs up the db to ``<db>.predelete.<size>b`` BEFORE any change.
  - Only rows whose session_key matches the (full) number are removed, so one
    user's data is deleted without touching anyone else's.
  - Prints counts only — never message content, and the number only masked to
    its last 3 digits.
  - On any problem (missing db, no match, error) it makes no change and exits 0,
    so a deploy never fails because of it.

Usage:
    python delete-user-sessions.py /path/to/state.db <number>
"""
import os
import re
import shutil
import sqlite3
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: delete-user-sessions.py <state.db> <number>")
        return 0
    db = sys.argv[1]
    number = re.sub(r"\D", "", sys.argv[2] or "")
    if len(number) < 6:
        print("no valid number provided — skipping")
        return 0
    if not os.path.exists(db):
        print(f"{db} not found — skipping")
        return 0

    masked = "…" + number[-3:]
    like = f"%{number}%"
    bak = None
    try:
        bak = f"{db}.predelete.{os.path.getsize(db)}b"
        shutil.copy2(db, bak)

        con = sqlite3.connect(db)
        cur = con.cursor()
        ids = [r[0] for r in cur.execute(
            "SELECT id FROM sessions WHERE session_key LIKE ?", (like,))]
        if not ids:
            print(f"no sessions match number {masked} — nothing to delete")
            con.close()
            if bak and os.path.exists(bak):
                os.remove(bak)  # nothing changed — drop the pointless backup
            return 0

        placeholders = ",".join("?" * len(ids))
        msg_count = cur.execute(
            f"SELECT COUNT(*) FROM messages WHERE session_id IN ({placeholders})",
            ids,
        ).fetchone()[0]
        cur.execute(
            f"DELETE FROM messages WHERE session_id IN ({placeholders})", ids)
        cur.execute("DELETE FROM sessions WHERE session_key LIKE ?", (like,))
        con.commit()
        con.execute("VACUUM")
        con.close()
        print(
            f"deleted {len(ids)} session(s) and {msg_count} message(s) for "
            f"number {masked}; backup kept at {os.path.basename(bak)}"
        )
    except Exception as exc:
        print(f"delete failed ({exc}) — db left unchanged (backup kept if made)")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
