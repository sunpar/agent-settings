# agent-settings

Global settings, skills, and plugins for Claude Code, Codex, and OpenCode.

- `AGENTS.md`: core global instructions (`CLAUDE.md` symlinks to it). Live at `~/.claude/CLAUDE.md`, linked from `~/.codex/AGENTS.md` and `~/.agents/AGENTS.md`.
- `skills/`: [tstack](https://github.com/t3dotgg/tstack) at `1085050` (MIT, see `skills/LICENSE-tstack`), plus `delegate`.
- `plugins/pstack/`: [pstack](https://github.com/cursor/plugins/tree/main/pstack) 0.15.29 (MIT).
- `plugins/claude-settings-compat/`: local marketplace used by both tools (see its `provenance.json`).
- `hooks/`: edit-check hooks shared by Claude Code and Codex (`~/.claude/hooks`, `~/.codex/hooks`).
- `claude/`: `~/.claude/settings.json` (plugins, marketplaces, permissions, hooks, env), `statusline.sh`, `rules/`, `references/`, `scripts/`.
- `codex/`: `~/.codex/config.toml` (plugins, marketplaces, MCP servers), `hooks.json`, `rules/default.rules`. Machine state is stripped: project trust list, desktop/notice/hook-trust state, connector approvals, and the ChatGPT-app-managed `node_repl` MCP.
- `opencode/`: `~/.config/opencode/opencode.json`.

Claude Code has no user-scope MCP servers; its MCPs come from plugins and claude.ai connectors.
