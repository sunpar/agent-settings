#!/usr/bin/env python3
"""Make the agent account for untracked files it left before it stops.

Wired as a SessionStart and Stop hook for Claude Code and Codex. Reviews kept
finding deliverables missing from the change (a migration, a doc it depends
on) and strays left behind (an unrelated uv.lock). SessionStart records when
the session began. Stop lists untracked, non-ignored files modified since
then, each path once per session, and blocks the stop with that list so the
agent adds, deletes, or explains each.

A session with no SessionStart record (one already running when the hook was
installed) starts at its first stop, so files from before that stop go
unlisted. A repo rooted at $HOME is skipped: listing a whole home directory
on every stop is not worth it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

STATE = Path.home() / ".cache" / "agent-hooks" / "untracked"
MAX_LISTED = 20


def untracked(top: Path, since: float) -> list[str]:
    """List untracked, non-ignored paths holding a file modified since a time.

    Args:
        top (Path): Repository root.
        since (float): Earliest modification time to report, in epoch seconds.

    Returns:
        (list[str]): Sorted paths relative to top. A file inside an untracked
            directory is reported as that directory, ending with "/".
    """

    def ls(*flags: str) -> list[str]:
        out = subprocess.run(
            [
                "git",
                "-C",
                str(top),
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                *flags,
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return [path for path in out.split("\0") if path]

    dirs = [entry for entry in ls("--directory") if entry.endswith("/")]
    changed = (path for path in ls() if (top / path).lstat().st_mtime >= since)
    return sorted(
        {next((d for d in dirs if path.startswith(d)), path) for path in changed}
    )


def main() -> None:
    event = json.load(sys.stdin)
    state = STATE / f"{event['session_id']}.json"
    if not state.exists():
        state.parent.mkdir(parents=True, exist_ok=True)
        state.touch()
        # The start is the state file's own mtime, not time.time(): Linux stamps files from a
        # coarser clock, so a file written just after time.time() can carry an earlier mtime.
        state.write_text(json.dumps({"start": state.stat().st_mtime, "listed": []}))
    if event["hook_event_name"] != "Stop" or event["stop_hook_active"]:
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
    session = json.loads(state.read_text())
    new = [p for p in untracked(top, session["start"]) if p not in session["listed"]]
    if not new:
        return
    shown = new[:MAX_LISTED]
    state.write_text(
        json.dumps({"start": session["start"], "listed": session["listed"] + shown})
    )
    more = (
        f"\n  ...and {len(new) - len(shown)} more, listed at a later stop"
        if len(new) > len(shown)
        else ""
    )
    reason = (
        f"Untracked files changed during this session in {top}:\n"
        + "\n".join(f"  {p}" for p in shown)
        + more
        + "\nFor each one: add it to the change if it belongs to the work, delete it if it is a stray"
        " you created (an unrelated lockfile, a scratch script), or tell the user why it stays"
        " untracked. Leave files you did not create alone."
    )
    print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
