---
name: deslop
description: Use when asked to deslop, clean up, simplify, or refactor code without behavior changes, or to review changed code for unnecessary complexity, wasted work, or comments.
---

# Deslop code

## Establish scope

Follow the applicable `AGENTS.md` files and repository conventions. Use the
paths, diff, branch, PR, or revision range the user names. Treat focus text
after `$deslop` as a constraint within that scope. For example,
`$deslop src/api/ focus on reducing nesting` limits edits to `src/api/` and
prioritizes control flow. Apply the cleanup unless the user asks for findings
only.

Without a named scope, start with changes made in the current task. If you
cannot identify them, use the working-tree diff as the candidate scope.
Leave unrelated user changes and hunks alone. When the request calls for
reviewing branch changes, resolve the base from the PR target or branch
context. A stacked PR can target another topic branch. Use the remote default
only when it fits the evidence. If the base is ambiguous, state the comparison
you used and surface the ambiguity if it matters.

For branch comparisons, inspect the merge-base diff to `HEAD`. Include staged,
unstaged, and untracked changes that belong to the requested scope. Judge the
current contents. Read outside the scope for context, keep edits inside it,
and preserve the Git index. For a partially staged file, use the
[read-only Git example](references/examples.md#choose-the-comparison-for-a-stacked-pr).

## Simplify with evidence

- **Reuse.** Search adjacent code and shared modules for an existing helper.
  Compare contracts, callers, and side effects before replacing duplication.
  Check registration, configuration, and public exports before deleting code.
- **Simplification.** Remove dead code, debugging remnants, unnecessary nesting,
  derivable state, speculative abstractions, and needless type escapes. Use
  clear names and idioms already used in the repository. Keep abstractions
  that express domain intent or handle a boundary.
- **Efficiency.** Look for repeated computation or I/O, blocking work in
  startup or hot paths, and callbacks that retain data they never use. Change
  scheduling or lifetime only when the order, failure, and resource contracts
  still hold. Verify the work eliminated at the real entry point.
- **Placement.** Trace a special case to the code that owns the rule. Prefer a
  fix there when it fits the scope and preserves the other callers' contracts.
  Leave broader redesigns and suspected correctness bugs as findings.

Make local, reviewable edits with the existing dependencies. Preserve public
contracts, including signatures, schemas, configuration keys, CLI flags,
serialized formats, and externally consumed text. Compare outputs, errors and
their timing, ordered side effects, and relevant cache, retry, timeout,
transaction, and concurrency behavior. Trace the paths into a guard, catch, or
fallback before removing it. Preserve authorization, validation, resource
handling, persistence, and compatibility. Leave uncertain edits alone. When
editing tests, retain independent expectations and distinct coverage for
success, errors, persistence, and compatibility.

Read the relevant [worked example](references/examples.md) when a guard,
fallback, cast, registered caller, test, or repeated operation looks
redundant, or when moving a rule could affect other callers.

## Make comments earn their place

Make the logic readable on its own. Use names that express intent and control
flow the reader can follow directly. When behavior permits, express a
constraint in the existing types or structure. Remove narration and any
comment that the clearer code has made redundant.

Keep only comments that carry information a reader needs and cannot infer
from the code. Record the shortest useful explanation of a compatibility
requirement, ordering dependency, or workaround next to the decision.
Preserve public API documentation, required headers, and directives
consumed by tools.

## Verify and report

Choose focused tests for the contracts touched. Run a baseline when practical
and rerun the relevant tests after editing. Run applicable type, lint, and
format checks. Broaden coverage for shared code or boundary changes. Review
the final diff for scope and behavior, including staged overlap.

Report the scope, edits, checks, and any verification gaps or pre-existing
failures. A clean review is a valid result when the evidence supports no edit.
