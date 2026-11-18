#!/usr/bin/env python3
"""Make the agent account for untracked files it left before it stops.

Wired as a SessionStart and Stop hook for Claude Code and Codex. Reviews kept
finding deliverables missing from the change (a migration, a doc it depends
on) and strays left behind (an unrelated uv.lock). SessionStart records when
the session began. Stop lists untracked, non-ignored files modified since
then, each path once per Git root per session, and blocks the stop with that
list so the agent adds, deletes, or explains each.

A session with no SessionStart record (one already running when the hook was
installed) starts at its first stop, so files from before that stop go
unlisted. A repo rooted at $HOME is skipped: listing a whole home directory
on every stop is not worth it.
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path

STATE = Path.home() / ".cache" / "agent-hooks" / "untracked"


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
            check=True,
        ).stdout
        return [os.fsdecode(path) for path in out.split(b"\0") if path]

    dirs = [entry for entry in ls("--directory") if entry.endswith("/")]
    changed = (path for path in ls() if (top / path).lstat().st_mtime >= since)
    return sorted(
        {next((d for d in dirs if path.startswith(d)), path) for path in changed}
    )


def display_path(path: str) -> str:
    return path if path.isprintable() and "\\" not in path else repr(path)


def handle_event(event: dict, state: Path) -> None:
    pending = state.with_suffix(".tmp")
    if not state.exists():
        pending.touch()
        # Linux can stamp files from a coarser clock, so use a filesystem mtime.
        pending.write_text(json.dumps({"start": pending.stat().st_mtime, "listed": {}}))
        pending.replace(state)
    if event["hook_event_name"] != "Stop" or event["stop_hook_active"]:
        return
    root = subprocess.run(
        ["git", "-C", event["cwd"], "rev-parse", "--show-toplevel"],
        capture_output=True,
    )
    if root.returncode:
        return
    top = Path(os.fsdecode(root.stdout.removesuffix(b"\n")))
    if top == Path.home():
        return
    session = json.loads(state.read_text())
    if isinstance(session["listed"], list):
        # Legacy entries have no Git root, so keep the start and report them afresh.
        session["listed"] = {}
    listed = session["listed"].setdefault(str(top), [])
    seen = set(listed)
    new = [path for path in untracked(top, session["start"]) if path not in seen]
    if not new:
        return
    listed.extend(new)
    pending.write_text(json.dumps(session))
    pending.replace(state)
    reason = (
        f"Untracked files changed during this session in {display_path(str(top))}:\n"
        + "\n".join(f"  {display_path(path)}" for path in new)
        + "\nFor each one: add it to the change if it belongs to the work, delete it if it is a stray"
        " you created (an unrelated lockfile, a scratch script), or tell the user why it stays"
        " untracked. Leave files you did not create alone."
    )
    print(json.dumps({"decision": "block", "reason": reason}))


def main() -> None:
    event = json.load(sys.stdin)
    state = STATE / f"{event['session_id']}.json"
    state.parent.mkdir(parents=True, exist_ok=True)
    with state.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        handle_event(event, state)


if __name__ == "__main__":
    main()
