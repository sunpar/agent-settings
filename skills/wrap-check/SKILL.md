---
name: wrap-check
description: Audit a Claude Code desktop session for loose ends, then either offer to archive it or lay out the remaining work as tasks to start here or in new sessions. Use for /wrap-check and whenever the user asks "anything left?", "are we done here?", "can I archive this?", "is it safe to close this session?", "what's still open?", or wants to wind a session down, even if they don't name the skill. Also use when the user points at another session and asks whether it's finished.
---

# Wrap Check

Answer three questions about a session, in order: is anything left, and if
not, can it be archived safely; if so, what can be started and where. This is
an audit. Don't do the remaining work, and never archive without an explicit
yes in chat.

## Pick the target

The target is this session unless the user names another one. For another
session, find it with `mcp__ccd_session_mgmt__list_sessions`, read its
history with `mcp__ccd_session_mgmt__list_events`, and run the repo checks in
its folder or worktree (from `get_session`). If the user hands you a
transcript file and a folder instead, audit those.

## Find what's left

Work through every check. Each is cheap, and the one you skip is the one that
loses work.

**Conversation.** Read the user's messages from the start, not just the
last turn.

- Each request: done, partly done, or dropped? Later corrections replace
  earlier asks.
- Promises made and not kept: "I'll do X next", "follow-up", "separate PR",
  "later", "not verified", "couldn't test".
- Pending or in-progress task-list items.
- Questions the user asked that never got an answer, and questions the
  assistant asked that the user never answered.
- Session cards proposed but never started or dismissed.

**Claims.** The transcript is the session's own account of its work, and it
can be wrong. Before counting a request as done, check each concrete claim
against the repo: files "added" or "changed" appear in the commits
(`git show --stat`), "committed" is in `git log`, "pushed" matches the
upstream, a named test exists. Rerun a test the transcript says passed only
when it's quick and named. A claim the repo contradicts is work left; one you
can't check is "unverified", not done.

**Repo.** Run in the target's folder, read-only:

- `git status --short`, `git stash list`
- `git log @{u}..` for unpushed commits. No upstream means nothing is
  pushed, unless the PR merged and the branch was deleted afterward.
- `git worktree list` and `get_session` to see whether the session owns a
  worktree. Archiving deletes that worktree by default, so uncommitted or
  unpushed work there is lost on archive. Treat it as a blocker, not a nit.

**PR.** `mcp__ccd_pr__get_status`, or `gh pr view --json
state,mergeable,statusCheckRollup,reviewDecision,autoMergeRequest` without it.
Open with failing or pending CI, requested changes, or conflicts means work
is left. Merged or closed means that part is done.

**Live work.** Running background shell tasks, Monitors, crons or scheduled
wakeups this session created, and `list_sessions {"linked": true}` for side
sessions still working or waiting on the user. A session with live work isn't
done even when the code is, and the app refuses to archive it.

**Deliverables.** Files the user needs that exist only in the scratchpad or
`/tmp`. Archiving doesn't delete those, but nobody will find them again.

## Report

Lead with one verdict line, then only the evidence that supports it. Keep
each item to a line: what's left and the proof (`3 files uncommitted in
worktree`, `CI failing on lint`, `user asked for dark mode, never done`).

### Done: safe to archive

Every check came back clean. Say so in one line with the evidence (clean
tree, pushed, PR merged, nothing running). Then call
`mcp__ccd_turn__wrap_up` with the ask "Archive this session?" and buttons
"Archive" and "Keep it".

When the user says yes, write your last message first, then call
`mcp__ccd_session_mgmt__archive_session` with `session_id: "self"` (or the
target's id) and a short `reason`. The conversation ends when the call
succeeds, so nothing after it is seen. If the result says the session wasn't
archived (pinned, open on screen, side session still working), tell the user
why.

### Waiting on you

Only the user can move it forward: a PR approval, a merge, a credential, an
answer to an open question. List those. Offer no session cards for them. If
nothing else is left, say the session can be archived once they're done.

### Work left

List every item, then sort each into one of two homes using the same test
as the app's own session rules:

- **Here.** It acts on what this session found or built, or it's a few tool
  calls. A new session would have to rediscover everything. Examples:
  committing and pushing, fixing the CI failure on this PR, answering the
  open question.
- **New session.** It's a task of its own that a short brief can carry: it
  lands apart from this change, touches other files, or the user set it
  aside earlier. Examples: an unrelated bug noticed in passing, a refactor
  promised as a separate PR, docs for another package.

For "here" items, put the most important one in `wrap_up` as the ask with a
button that does it ("Commit and push", "Fix CI"), plus "Not now". If there
are several, name the rest in the closing message so the user can pick.

For each "new session" item, call `mcp__ccd_session__start_session` with
`initiation: "own_initiative"`, at most three per turn. Prefer
`context: "fresh"` and write a complete brief: `prompt` with the task, files,
and what done looks like; `background` (80+ characters) with the goal and
decisions so far. Write it for someone who never saw this conversation. Use
`"fork"` only when the task leans on this conversation and it is still short.
These are cards: nothing runs until the user clicks one.

If items in both homes exist, say which "here" work has to land before the
session can be archived, and whether new-session cards can start now or must
wait for it.

## Example

> **Not done: 1 blocker, 2 follow-ups.**
>
> Here
>
> - Worktree has 2 uncommitted files (`api/auth.ts`, `api/auth.test.ts`).
>   Archiving now would delete them.
>
> New session (cards below)
>
> - Flaky `checkout.spec.ts` you noticed at 14:02, unrelated to auth.
> - README for the new `/v2/token` endpoint, promised as a separate PR.

`wrap_up` ask: "Commit and push the auth changes?" with "Commit and push" and
"Not now".
