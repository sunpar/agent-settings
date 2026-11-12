# agent-settings

Global instructions, skills, hooks, settings, and plugins for Claude Code and Codex, installed from one repo.

- `AGENTS.md`: global instructions for both tools (`CLAUDE.md` symlinks to it).
- `skills/`: [tstack](https://github.com/t3dotgg/tstack) at `11e37a7` (MIT, see `skills/LICENSE-tstack`), plus `delegate`.
- `plugins/`: the `agent-settings` local marketplace for both tools. Holds [pstack](https://github.com/cursor/plugins/tree/main/pstack) 0.15.36 (MIT) and the plugins listed in `plugins/PROVENANCE.json`.
- `hooks/`: edit-check hooks shared by both tools.
- `claude/`: Claude Code settings, statusline, and rules.
- `codex/`: Codex `config.toml` and approved command rules.
- `opencode/`: OpenCode config. Not installed.

## Install

```sh
git pull && ./install
```

`./install` needs [uv](https://docs.astral.sh/uv/). It prints each change, then links, renders, and merges the files into `~/.claude`, `~/.codex`, and `~/.agents`. Settings and config files are merged, so keys that Claude Code and Codex write themselves (permission approvals, project trust, hook trust) are kept. Run it again any time. When nothing changed it prints `up to date`.

- `./install --dry-run` prints the plan and writes nothing.
- `./install claude` or `./install codex` installs one tool only.
- Every file it replaces or removes is copied first to `~/.local/state/agent-settings/backups/<UTC timestamp>/`.
- After the first run, and whenever `hooks/hooks.json` changes, Codex asks you to trust the hooks again.

To update pstack, copy upstream `harness/pstack/claude-code` over `plugins/pstack/` and bump the version in `plugins/pstack/plugin.json` and `plugins/pstack/.claude-plugin/plugin.json`.
