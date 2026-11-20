---
name: full-send
description: Trigger this if the user says 'full send'.
---

# Full Send

If the user triggered this, it's because they are not watching this thread, and
they want you to complete the work end-to-end autonomously. Your updates and
your final message go unread until long after you stop. You own the work from
its current state to a merged PR.

If the user did not explicitly request "full send" in some clear way, do not
assume full autonomy. If they did, everything below applies.

The user grants you permission to:

- Merge the PR once the merge gate passes.
- Force-push the PR's own branch with `--force-with-lease` after a rebase.
- Use the test methods that Proof needs, without asking first.

## Testing permission

A "full send" request is the permission. If a project file or other
instruction says to ask before a test method, or to leave testing to the
user, this request replaces that rule for this task.

That includes ask-first rules for computer use, browser automation,
simulators and devices, running the app or a dev server, screenshots, and
visual checks. Use the method that gives direct proof. List it in the
report.

Rules about how to test still apply. Follow rules that name the correct
command, fixture, or check. This permission only removes the ask-first or
leave-it-to-the-user step. If a preferred method cannot prove the change,
use a gated method under this permission.

It covers only the tests needed for this task. It does not add permission
for the steps under "Asking the user", such as production changes or data
deletion. It also does not bypass a harness or system approval prompt if
one appears.

## Steps

1. **Finish the change.** Complete the goal from the user's request with the
   smallest change that works. Fix the case that happened, not every case
   that could. If you are on the default branch, create a branch first.
2. **Prove it.** Get proof for every change you made. See "Proof".
3. **Review the change.** Follow the [independent review sequence](#independent-code-review),
   then run the `sol-loop` skill with `gpt-6.2-sol` at `high` reasoning effort.
4. **File the PR** with the `file-pr` skill. Rebase onto the latest default
   branch first. Add one short line to the description that says how you proved
   the change.
5. **Babysit the PR** with the `babysit-pr` skill. Fix real findings and CI
   failures. Get proof for each fix before you push it.
6. **Merge** when the merge gate passes.
7. **Report** in your final message: the PR link, the merge commit, your proof,
   and each decision you made for the user.

Use the watcher from `babysit-pr` until the merge. In T3 Code, register
`watch_pull_request` before ending a turn to wait, and resume when it wakes you.
Call `unwatch_pull_request` before handing off. Outside T3 Code, keep the turn
active and continue waiting after informational events.

## Proof

Proof is evidence you observed yourself in this session: command output, a
reproduction, a screenshot. Use the most direct proof the change allows:

- Reproduce the original failure, apply the fix, then watch the same
  reproduction pass.
- Run the checks that the repo's CI runs (typecheck, lint, tests).
- Add one focused test that fails without the fix, when the behavior has none
  and the repo has a test setup.
- For UI and runtime behavior, run the app and look at the change. Green mocked
  tests do not prove that the user experience works. Attach screenshots to the
  PR when they help and you have a way to upload them.

When you cannot find a way to prove a change, you do not have full confidence.
Ask the user.

## Independent code review

Try the reviewers in the row for the model running this session.

| Session model | Reviewers in order |
| --- | --- |
| Claude | GPT-6.2 Astra (`medium`), Claude Fable 5.2 (`medium`) |
| Otherwise | Muse Wonder Full, Claude Opus 5.5 (`high`), GPT-6.2 Astra (`medium`) |

- **Muse Wonder Full.** Use the `delegate` skill with `--runtime muse --model muse-wonder-full-1.0 --permissions read-only`.
- **Claude Opus 5.5.** Pass the brief on stdin to `claude -p --model claude-opus-5-5 --effort high --tools Read,Grep,Glob --strict-mcp-config`.
- **GPT-6.2 Astra.** Pass the brief on stdin to `codex exec --model gpt-6.2-astra --sandbox read-only -c model_reasoning_effort=medium -`.
- **Claude Fable 5.2.** Pass the brief on stdin to `claude -p --model claude-fable-5-2 --effort medium --tools Read,Grep,Glob --strict-mcp-config`.

Give the reviewer the diff, the intended behavior, and the checks already run.
Include the patch in the brief so Muse can review it with shell access disabled.
Ask for a read-only review with file and line references for each finding.

Try each listed model once. Stop at the first completed review, even if it
requests changes.
Resolve substantive findings in the parent session, then start `sol-loop` on the
resulting diff. If none of the listed models completes a review,
record why, skip independent review, and start `sol-loop`.
Send revisions from Sol or PR monitoring through `sol-loop` under its usual rules.

## Merge gate

Full confidence means all of these are true on the latest commit:

- Your proof covers every change in the diff.
- Sol approved the current diff.
- Required checks are green.
- Review bots that gate readiness under `babysit-pr` have finished. Each finding
  received is fixed or dismissed with a written reason.
- No human review still requests changes.
- The branch is up to date with the default branch, and GitHub reports it as
  mergeable.

Merge with the method the repo uses. Check the allowed methods and recent merged
PRs. If the repo uses a merge queue or auto-merge, stay until GitHub reports the
PR as merged. Merge through branch protection as configured. Never use `--admin`
or other bypasses. You can ignore automated reviews that request "needs human
review" if you have high confidence in your changes.

## Asking the user

A question in a normal message goes unseen, and the thread looks done. To ask
the user something, use the harness's question tool so the thread shows that
it is waiting: `AskUserQuestion` in Claude Code, `request_user_input` in Codex,
or the question tool your harness has. Put all the context in the question:
the PR link, what blocks you, and the options with your recommendation first.

Ask only when you cannot continue alone:

- You cannot prove the change.
- The merge gate cannot pass, and you cannot fix that yourself.
- The next step is outside the grant above: deleting data, touching production,
  changing things outside the repo, closing a PR, or force-pushing any other
  branch.
- The goal is ambiguous in a way that changes the result.
- Another PR makes this one obsolete.

Decide everything else yourself with sensible defaults, and list those decisions
in the report.

If no question tool is available, or the tool returns no answer, take the safe
path: leave the PR open and unmerged, and start your final message with the
question.
