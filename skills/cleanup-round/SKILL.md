---
name: cleanup-round
description: Audit disk usage and clean up development worktrees, branches, caches, temporary files, or idle agent sessions while preserving unfinished work and retained evidence. Use for cleanup rounds, space reclamation, or worktree consolidation.
---

# Clean up development resources

Match the requested scope and mode. A disk-usage audit is read-only. A whole development cleanup can cover worktrees, branches, caches, temporary files and idle sessions; a request for one category does not authorize the others. Carry forward explicit exclusions, such as a backup, dataset, volume or active project. Cleanup alone does not authorize integrating code, retiring research data, or deleting remote branches.

Discover the operating system, repositories, host tools and agent capabilities. Keep this workflow portable: do not assume home-directory layouts, a Git host, a desktop app, or session-specific project names.

## Inventory disk use and activity

Record free space before and after on the same volume, using `df -k` or the platform equivalent. Use `du -sk` for candidate sizes, but distinguish logical size, allocated size and actual free-space change. APFS clones, hard links and sparse files can make totals misleading. Report concurrent disk activity as a limit on attribution rather than claiming every change came from cleanup.

Inventory registered checkouts with `git worktree list --porcelain`. For a machine-wide request, discover repositories across current projects, agent worktree roots and old task folders, then deduplicate by Git common directory. Count existing linked worktrees separately from primary checkouts, missing registrations and restored archive folders whose `.git` pointers no longer work. Do not treat broken pointers as permission to delete recovery data.

Use available session tools and process inspection to establish ownership. Check working directories, open files and relevant command arguments (`lsof` and `ps` where available), without exposing secrets in the report. A task can run from its primary checkout while editing several worktrees. Protect its active checkouts and still-needed evidence, not just its listed working directory. Keep the current session, locked worktrees and tool-managed spares. If activity cannot be determined, leave the affected candidate and explain the uncertainty.

## Establish what is integrated

Find the authoritative repository and its actual default branch. An old task clone may have stale local `main`, no remote, or a retired hosting URL. Check the current canonical repository before classifying its work. During authorized cleanup, fetch without automatically pruning references; during a preview, use read-only remote queries and label stale local evidence. On GitHub, use `gh` for repository and pull-request information.

Classify each exact worktree HEAD using commands and evidence recorded in a decision ledger:

- **Integrated:** HEAD is an ancestor of the current default branch, or is contained in the recorded head of a merged PR. The latter handles squash merges. Inspect diffs when commits were selectively ported; an empty `git cherry` result alone does not account for merge commits or prove equivalence.
- **Reviewed as superseded or partially integrated:** use a prior authorized review only if its source HEAD still matches. Record where useful changes landed and why the rest was rejected. This is a separate disposition, not a claim that the entire branch merged.
- **Retain:** useful unmerged work, local changes, active use, open PRs, or missing evidence. A deleted upstream, branch name, age, or clean status is not integration proof.

If the user separately requests evaluation or completion, compare the remaining behavior with current main before merging old stacks. Complete useful missing work through the requested review, test and merge workflow. Keep rejected experiment history; do not reintroduce a failed model or obsolete default merely to make its branch mergeable. Cleanup can then remove an explicitly retired checkout while retaining its commits in a branch or tag. Anchor detached commits before removing their last checkout.

## Preserve files outside Git before removal

Inspect tracked and staged changes, untracked files, and ignored files. Use `git status --porcelain=v1 --untracked-files=all`, `git diff HEAD`, and `git ls-files --others --ignored --exclude-standard -z`. Clean Git status can coexist with valuable databases, saves, raw inputs, reports, screenshots or verification logs. Keep unique local source changes unless their disposition is separately authorized.

Compare proposed duplicates by content hash, not names or sizes. Verify that their retained copy is outside every planned removal target. Treat changing databases as snapshots rather than durable duplicate copies. Identify generated dependencies or build output by their owning tool and reproducible inputs; an ignored path or a directory named `cache` is insufficient.

For an otherwise removable worktree, preserve needed ignored files in an archive outside all removal targets. Include the complete state needed for restoration, such as a database and its WAL/SHM companions, only when no writer is active. Record original paths, HEAD, retained Git refs, file inventory, sizes, permissions, symlink targets and SHA256 hashes. Preserve symlinks as links; do not follow them into unrelated data. Protect archives containing private configuration with appropriate local permissions.

Verify the archive by reading its members and comparing their contents with the manifest. Verify source files and inventory remain unchanged immediately before deletion. If files change, a copy fails, a writer appears, or verification is incomplete, retain the source. Merely creating a tarball is not sufficient. Keep the archive manifest and cleanup receipt after removing the checkout.

## Retire datasets only when requested

When explicitly replacing bulky experiment data with summaries, first preserve the question, motivation, code and input identities, settings and seeds, results, failed or negative outcomes, limitations and lessons. Use repository results and relevant agent-session records; distinguish observed findings from later interpretation. Retain compact evidence and explain which reruns become impossible after raw-data deletion. If the user requests repository publication, verify that the preservation record reached the requested committed or merged state before deleting the authorized data. A worktree cleanup request alone does not authorize this tradeoff.

## Clean other authorized resources

For caches and temporary files, verify ownership, activity and rebuildability; prefer the owning tool's documented cleanup command. Distinguish logs and downloaded runtime files from local databases, browser profiles, session disks and backups. Preserve active locks and named data volumes. Handle Docker resources, package stores and downloaded browser binaries only within the requested scope, with their own usage checks.

Archive idle sessions only when session cleanup is in scope and the agent application supports it. Keep current, pinned or running sessions, reminders and sessions associated with open PRs. Preserve session data and report application refusals. Archiving a chat and removing its worktree are separate actions.

## Recheck, execute and report

A preview must not fetch, prune references, create archives, archive sessions or delete files. For authorized cleanup, recheck HEAD, local changes, locks, activity, ignored-file inventory, archive integrity and open PRs immediately before each removal. If the candidate changed, reclassify it. Use `git worktree remove` without force; report refusals instead of bypassing them.

Worktree removal does not require branch deletion. When branch cleanup is also in scope, keep checked-out, default and protected branches and branches used as an open PR's head or base. Prefer safe local deletion. Before force-deleting a squash-merged local branch, prove its exact tip is included in the merged PR. Remote branch deletion requires explicit authorization covering the branch, a verified remote tip and merged PR, and a lease or equivalent concurrency check. Do not delete other people's branches without explicit authorization.

Keep an action receipt with source paths and HEADs, classification evidence and commands, archive locations and hashes, actual removal commands, failures and reasons for retention. Recount with `git worktree list --porcelain`; verify removed paths are absent and retained history refs still contain their commits. Report linked-worktree counts by repository, measured free-space change, archive size, and remaining active or unique work. State whether primary checkouts, stale registrations and archive copies are excluded from the count.

If a local installation retains the legacy machine-specific `scripts/cleanup.py`, do not use it for this workflow: its dry run fetches and prunes Git references, and a normal run combines remote branch deletion with broad cache cleanup.
