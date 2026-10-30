# Claude Code Settings

Guidance for Claude Code and other AI tools. Structured around [Andrej Karpathy's observations on LLM coding pitfalls](https://x.com/karpathy/status/2015883857489522876): surface assumptions, don't overcomplicate, make surgical changes, verify before moving on.

## Core Principles

**Do what was asked. Nothing more, nothing less.** This year is 2026.

**Delete > Replace > Add.** Before any change, answer in order: what can I delete, what can I replace, and only then, what must I add?

- **Guard nothing, relocate the trigger.** A fix that adds a condition to mask bad behavior (a staleness check, an is-ready flag, a try/except around broken logic) is wrong by default. Move the logic to the code path that should own it, then delete what got it wrong. No defensive programming unless you state the motivation and the user approves.
- **Bugfixes are net-negative by default.** If a fix adds more lines than it removes, justify in one sentence why deletion and relocation were impossible.
- **Search before creating.** Use `rg` to find existing helpers. Fold duplicates into one shared utility; three similar lines beat a helper nobody else calls. Understand and delete broken or duplicated code instead of keeping it "to be safe".
- **This guidance is code: additions require deletions.** To add a rule, remove or merge one.

Ask yourself: "What can I delete instead of add, and does this trace to what was asked?"

## Working Rules

- Reflect on tool results, check related code for consistency, run independent operations in parallel, and verify before finishing. Prefer editing existing files; never create docs (*.md, README) unless asked.
- Before committing to an approach, and after two failed attempts at the same problem, get a second opinion with `/codex-advisor`.
- Use the `writing-guidelines` skill to review documentation or interface copy.
- Use the `anthropic-frontend-design` or `openai-frontend-design` skill when creating or reshaping a UI.

## GitHub

Use `gh` CLI for all GitHub interactions. Never clone repositories to read code.

## Python Coding

Before writing Python, read the `python-guidelines` skill's `references/` files (idiomatic patterns, Zen of Python, Google style guide, Effective Python) before you write the code, not after. Key rules always in effect:

- **Package manager and paths**: Use uv (NOT pip) and pathlib, not os.path. Activate `.venv` or use `uv run python -c "..."`.
- **Verify before planning**: Run Python probes to test hypotheses. Integrate into existing code and match its patterns; don't assume or append.

## Testing

- While iterating, run only the tests that cover the change. Run the full suite once on the final commit before merge, not after every fix or review round.
- Keep routine tests local and offline: fixtures and local services, no production credentials or paid API calls. Cloud integration and E2E checks are explicit and opt-in.
- Use the project's existing test and lint commands. Don't build repository tooling such as staged-snapshot gates, per-ref push verification, dependency-policy checks, hook installers, or PR wrappers unless asked.
- Leave production deployment jobs, their post-deploy smoke checks, and required statuses intact.

## Git

Ask yourself: "Would someone unfamiliar with this repo understand this commit message?"
