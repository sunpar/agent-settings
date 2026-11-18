---
name: wrap-check
description: Audit an agent session for unfinished work, unverified claims, or work that would be lost on close. Use when asked to run wrap-check, find loose ends, check whether this or another session is done, or decide if it is safe to close or archive.
---

# Check whether a session is ready to close

Audit the session and recommend what to do next. Keep the audit read-only: leave follow-ups, commits, pushes, merges, and new sessions for a separate request. A question about whether it is safe to archive is not authorization to archive.

## Identify the target

Use the current session unless the user names another one or supplies a transcript. Use available session history and workspace metadata to match the target to its files, repository, or worktree. If the target is ambiguous, ask which one to audit. Never substitute your current workspace for another session’s.

Use the host’s read-only session tools to fill gaps or refresh stale evidence. For Claude Desktop’s session tools and optional action cards, see [Claude Desktop](references/claude-desktop.md). If the host has no session tools, audit the available files and history and report in plain text.

## Check requests against evidence

- **Conversation:** Read the relevant history from the start. Track each request and later correction, promises, open questions, and pending tasks. Distinguish required work from ideas the user deferred or declined.
- **Claims and deliverables:** Verify material completion claims against files, commits, test output, or the destination where the user expects the result. Check that the user can still reach deliverables stored in scratch space, an ephemeral workspace, or the chat. Use a named, inexpensive local check when it would resolve a material gap and has no consequential side effects. A contradiction is unfinished work; missing evidence is unverified.
- **Local and remote state:** For Git work, run `git --no-optional-locks status --short --untracked-files=all`, `git stash list`, and `git worktree list --porcelain` in the target repository. Check commits with `git log` or `git show` and compare the branch with its upstream when configured. A missing upstream or a stale tracking ref tells you nothing conclusive about remote state. Confirm publication or integration when it matters. A merged review may account for a squash merge if it covers the local changes; a closed but unmerged review does not prove integration.
- **Reviews and live work:** When relevant, check the actual review, checks, and approvals (on GitHub, use `gh pr view` or `gh pr checks`). An open review can be the intended deliverable; flag unresolved checks, feedback, conflicts, or approvals when they affect the requested outcome. Look for related jobs, scheduled runs, or linked sessions still working or waiting for input. Note who or what can move them forward.
- **Closure risks:** Check what closing or archiving does in this host. Treat unique changes, commits, or deliverables as blockers when the action could discard them. Do the same for work that would be interrupted. If the consequences are unknown and could matter, leave archive safety unverified. A dirty shared workspace can be unrelated to task completion; flag it as a closure risk only if the action could affect it.

## Report the verdict

Lead with one verdict: ready to close, work remains, waiting on someone, or unable to verify. State archive safety separately if it differs. Cite the evidence that decides the verdict: a path, check result, review state, or specific request. Skip checks that do not apply and name missing evidence that could change the answer.

Group open items by next action when it helps:

- **Continue here:** Work that needs the session’s context, files, or existing review. Name the next step.
- **Hand off:** Work that can start from a short brief. Include the goal, relevant files or links, what done means, and any dependency that determines whether it can start now.
- **Waiting:** Name the person or external event needed and what it will unblock.

If the session is ready and archiving is useful, offer to archive it. Use a supported host action only with explicit authorization for that session, and recheck any state that could have changed before acting. With no archive tool, report whether the user can close or archive it themselves. Never substitute deletion for archiving.
