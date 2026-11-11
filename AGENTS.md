# Agent Guidance

Guidance for Claude Code, Codex and other coding agents: surface assumptions, don't overcomplicate, make surgical changes, verify before moving on.

Project instruction files are more specific than this one: where they differ, follow the project's file.

## Core Principles

**Do what was asked. Nothing more, nothing less.**

**Delete > Replace > Add.** Before any change, answer in order: what can I delete, what can I replace, and only then, what must I add?

- **Guard nothing, relocate the trigger.** Inside code you own, a condition that masks bad behavior (a staleness check, an is-ready flag, a try/except around broken logic) is wrong by default: move the logic to the code path that should own it, then delete what got it wrong. At trust boundaries (CLI args, request bodies, files, env, third-party payloads), validate before the first side effect, reject duplicates and unknown values, and fail loudly rather than default to a plausible value (`.get(k, 0)`, `?? 0`, `or {}`). Other defensive code needs a stated motivation and the user's approval.
- **Bugfixes are net-negative by default.** If a fix adds more lines than it removes, justify in one sentence why deletion and relocation were impossible.
- **Search before creating.** Use `rg` to find existing helpers. Fold duplicates into one shared utility; three similar lines beat a helper nobody else calls. Understand and delete broken or duplicated code instead of keeping it "to be safe".
- **This guidance is code: additions require deletions.** To add a rule, remove or merge one.

## Working Rules

- When a change renames or alters a field, flag, route, path, command or format, `rg` for every definition, reader, test and doc that uses it and update them in the same change.
- Before finishing, check each requirement in the request against the diff and `git status`, and name any you did not meet.
- In docs and reports, every claim names the command that measured it. Prefer editing existing files; never create docs (*.md, README) unless asked.
- Write commit messages and replies for someone who hasn't seen your working: define any internal name, number or path you mention, and say what it means for the user.
- Before committing to an approach, and after two failed attempts at the same problem, get a second opinion with `/codex-advisor`.
- Use the `writing-guidelines` skill to review documentation or interface copy.
- Use the `anthropic-frontend-design` or `openai-frontend-design` skill when creating or reshaping a UI.

## GitHub

Use `gh` CLI for all GitHub interactions. Never clone repositories to read code.

## Python Coding

Before writing Python, read the `python-guidelines` skill's `references/` files. Key rules always in effect:

- **Package manager and paths**: Use uv, not pip, and pathlib, not os.path. Activate `.venv` or use `uv run python -c "..."`.
- **Verify before planning**: Run Python probes to test hypotheses. Integrate into existing code and match its patterns; don't assume or append.

## TypeScript and React

- **State follows its entity**: key or reset per-entity state (selection, drafts, error overlays) when the selected entity changes or disappears.
- **Only the latest request writes**: drop or abort responses from requests that are no longer current, and invalidate every cached query a mutation changes.
- **Say what actually happened**: loading, empty, error and stale data each render differently, and copy never claims more than happened (no "Saved" while edits remain, no bare "—").
- **Parse external data**: validate API responses where they arrive instead of casting with `as` or `!`.

## Testing

- A test for a change must fail without it: drive the real entry point, include a negative or near-miss input (empty, zero, duplicate key, malformed, another format), and assert literal expected values, not values computed by the code under test.
- While iterating, run only the tests that cover the change. Run the full suite once on the final commit before merge, not after every fix or review round.
- Keep routine tests local, offline and machine-independent: fixtures and local services; no production credentials, paid API calls, absolute paths, or reliance on this machine's tools, timezone or clock. Fixtures, docs and examples use synthetic data, never real names, amounts or account values. Cloud integration and E2E checks are explicit and opt-in.
- Use the project's existing test and lint commands. Don't build new repository tooling unless asked.
- Leave production deployment jobs, their post-deploy smoke checks, and required statuses intact.
