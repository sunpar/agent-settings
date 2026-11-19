# Epic delivery

## Find work that can start

Read the epic and its child issues with `gh`. Prefer GitHub’s sub-issue and dependency records, then use the epic’s explicit child list or dependencies where needed. Include nested children within the requested scope. Review issue status, acceptance criteria, and open PRs.

An issue is ready when its prerequisites are satisfied, its scope is clear, and it can proceed independently of active work. Consider shared interfaces, migrations, fixtures, and other overlapping changes. Preserve documented deferrals and evidence gates. If an otherwise blocked issue has a separately actionable deliverable in scope, dispatch only that deliverable and preserve the unresolved acceptance criteria.

## Use the capacity available

Before dispatching and whenever work changes phase, check recent CPU utilization, available cores, memory pressure, and other active builds or tests on that host. Estimate each ready worker’s near-term demand. Honor user and host limits. As a default, leave roughly a quarter of CPU capacity available and admit work while memory pressure is normal. Use short samples and the expected workload together. When capacity is uncertain, start one worker and measure before adding more. Pause new starts and stagger heavy tests when pressure rises.

Fill available capacity with ready, independent tickets. Follow the epic’s priorities and favor work that unblocks other tickets when priorities are equal. Track existing PRs under their current owners. Give each unassigned ticket one delivery session with a separate branch and worktree. Each session invokes `implement-and-merge` for its ticket and owns implementation, review, its PR, its final CI, and its protected merge. Give it its issue, scope, branch, prerequisites, and the coordination channel for gate requests and progress. Use a shared scratch directory for requests and grants if the sessions lack a common message channel.

## Coordinate the final gate and merge

Have workers request a gate window after review and the other required checks are ready. Reserve enough host capacity for the full local suite to finish under five minutes. If capacity is uncertain or CI runs near the limit, grant one full local gate at a time per host and defer other heavy tests during it.

Grant one gate-and-merge window at a time per repository and target branch. Use the same epic priorities and break gate ties by request order. The ticket owner fetches the latest base after receiving the window, runs its timed local gate on the reviewed PR head, and merges it through protection. Release the window on verified merge or when the owner returns to review, waits on an external prerequisite, or reports a blocker. The coordinator grants windows and tracks outcomes. Each ticket owner executes its own CI and merge.

## Refill and finish

Refresh worker and GitHub state when tickets finish, prerequisites change, or capacity returns. A dependency that requires merged code becomes ready after GitHub confirms the merge. Refill available slots as soon as eligible work exists. Use completion events or bounded rechecks while workers or transient load keep work pending.

Finish after verifying the merges and tracker dispositions, or when the remaining work is concretely blocked or deferred. Report merged PRs and commits, CI wall times, and remaining issues with their blockers. Apply the epic’s completion rule and the user’s authorization before closing it.
