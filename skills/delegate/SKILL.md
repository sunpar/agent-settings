---
name: delegate
description: Delegate a task to another coding agent (Claude Code, Codex, OpenCode, or Muse Code) and get its result back in this session. Use when the user types /delegate or asks to hand implementation, review, or investigation work to Codex, Claude, OpenCode, Muse, or "another agent" while this session keeps coordinating.
---

# Delegate

Hand an instruction to another coding-agent runtime with `agentctl`. You stay the coordinator: the child works
in its own session, by default on an isolated git worktree, and its result comes back into this session.

## Read the request

`/delegate <runtime> <instruction>`, for example `/delegate codex Review my uncommitted changes for
concurrency issues` or `/delegate claude-opus Implement the new API endpoints and run the tests`.

- **Runtime**: `claude`, `codex`, `opencode`, or `muse`. A suffix names a model: `claude-opus` means runtime `claude`,
  `--model opus`. Muse model ids keep their prefix: `muse-spark-1.3` means `--runtime muse --model
  muse-spark-1.3`. If no runtime is named or you don't recognize it, run `agentctl runtimes` and pick an
  installed one, or ask.
- **Permissions**: `workspace-write` by default. Use `read-only` for reviews and investigations that should not
  change code. Use `full` only when the user asks for it.
- **Return mode**: `notify` by default. Use `--mode wait` only for short tasks the user wants to block on.

## Write the brief

The child sees none of this conversation. Write a self-contained brief to a temporary file: the goal, the
files and paths involved, constraints, how to verify (which tests to run), and what to report. The child
starts from a snapshot of the current checkout that includes uncommitted and untracked files, so "my
uncommitted changes" means the same thing to it.

## Start it

```bash
agentctl delegate --runtime codex --prompt-file /tmp/delegate-brief.md
```

Add `--model`, `--permissions`, `--mode wait`, or `--cwd` as needed. `--isolation none` makes the child work
directly in this checkout; use it only for read-only tasks or when the user wants the edits in place.

`agentctl` talks to a local orchestrator on 127.0.0.1 and keeps state in `~/.agent-delegator`. If this
harness sandboxes shell commands, run `agentctl` with escalated (unsandboxed) permission.

The command prints JSON with `taskId`, `branch`, and `deliveryRoute`. Tell the user the task id, then carry
on with other work. Don't poll.

## When the result arrives

A message starting with `[agentctl] Delegated task …` arrives in this session. Then:

1. Run `agentctl result <taskId>` for the full report, outcome, validation, and artifacts.
2. Check both fields: `status` says whether the child process finished, `outcome` is the child's own verdict
   on the work. Inspect changes with `git diff <artifacts.base> <artifacts.branch>`.
3. Report to the user, or continue the same child session with
   `agentctl send <taskId> --prompt-file /tmp/followup.md`. Don't merge the branch unless the user asks.

If `deliveryRoute` is `none`, this harness has no push route. If it wakes you when a background task
finishes, as Muse Code does, run `agentctl wait <taskId> --timeout 3600` as a background task right away
and treat its output as the arriving result. Otherwise run `agentctl wait <taskId> --timeout 600` when the
user asks or when you need the result.

## Other commands

- `agentctl status` lists recent tasks; `agentctl status <taskId>` shows one task's progress.
- `agentctl cancel <taskId>` stops a running turn.
