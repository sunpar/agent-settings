#!/usr/bin/env python3
"""Make the agent account for untracked files it left before it stops.

Wired as a Stop hook for Claude Code and Codex. Reviews kept finding
deliverables missing from the change (a migration, a doc it depends on) and
strays left behind (an unrelated uv.lock). Untracked, non-ignored paths
modified since the session started are listed once per session: the hook
blocks the stop with that list so the agent adds, deletes, or explains each.

The session starts when its transcript was created. A session without a
transcript (an ephemeral Codex run) starts at its first stop, so files from
its first turn go unlisted. A repo rooted at $HOME is skipped: listing a
whole home directory on every stop is not worth it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

STATE = Path.home() / ".cache" / "agent-hooks" / "untracked"
MAX_LISTED = 20


def untracked(top: Path) -> list[str]:
    """List untracked, non-ignored paths under a repo, one entry per untracked directory.

    Args:
        top (Path): Repository root.

    Returns:
        (list[str]): Paths relative to top; directories end with "/".
    """
    out = subprocess.run(
        [
            "git",
            "-C",
            str(top),
            "ls-files",
            "--others",
            "--exclude-standard",
            "--directory",
            "-z",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [path for path in out.split("\0") if path]


def main() -> None:
    event = json.load(sys.stdin)
    if event["stop_hook_active"]:
        return
    root = subprocess.run(
        ["git", "-C", event["cwd"], "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if root.returncode:
        return
    top = Path(root.stdout.strip())
    if top == Path.home():
        return
    state = STATE / f"{event['session_id']}.json"
    if not state.exists():
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text("[]")
    clock = Path(event["transcript_path"]) if event.get("transcript_path") else state
    start = clock.stat().st_birthtime
    listed = set(json.loads(state.read_text()))
    new = [
        p
        for p in untracked(top)
        if p not in listed and (top / p).lstat().st_mtime >= start
    ]
    if not new:
        return
    state.write_text(json.dumps(sorted(listed | set(new))))
    more = f"\n  ...and {len(new) - MAX_LISTED} more" if len(new) > MAX_LISTED else ""
    reason = (
        f"Untracked files changed during this session in {top}:\n"
        + "\n".join(f"  {p}" for p in new[:MAX_LISTED])
        + more
        + "\nFor each one: add it to the change if it belongs to the work, delete it if it is a stray"
        " you created (an unrelated lockfile, a scratch script), or tell the user why it stays"
        " untracked. Leave files you did not create alone."
    )
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
