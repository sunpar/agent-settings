# Simulated app tool outputs

## get_session("self")
{"sessionId": "local_c40d", "title": "Switch exports to fetch_v2", "worktree": {"path": "./repo", "branch": "exports-fetch-v2", "base": "main"}, "pinned": false}

## ccd_pr get_status
{"pr": {"number": 431, "url": "https://github.com/acme/ledger/pull/431", "state": "OPEN", "checks": "PENDING", "reviewDecision": "REVIEW_REQUIRED", "mergeable": "MERGEABLE"}}

## list_sessions {"linked": true}
[{"sessionId": "local_d77e", "name": "docs-sync", "title": "Update API docs for fetch_v2", "state": "working"}]

## Background tasks, monitors, crons, wakeups
- bash task b3: `npm run e2e` (running, started 6 min ago)
