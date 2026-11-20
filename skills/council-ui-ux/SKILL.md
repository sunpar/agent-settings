---
name: council-ui-ux
description: Review an app's UI and UX with screenshots and independent council scores. Iterate to the requested score when the user asks for improvements. Supports reference-app comparisons.
---

# Council UI/UX

Run the app, capture its main screens and important states, and have each council member independently identify specific design issues and score the experience from 1 to 10.

For review-only requests, keep the app and PR read-only. Report the screenshots, findings, scores, and recommendations in chat, even if a PR is open. Stop after reporting.

When the user asks for improvements, implement them and repeat the review until **every required reviewer scores the current design at least 9/10**, unless the user sets a different target.

Focus on clarity, visual hierarchy, typography, spacing, consistency, and ease of use. Preserve existing functionality.

## Set up the review

Read the installed [council skill](../council/SKILL.md) for reviewer selection, model identities, fallbacks, and delegation. Follow this skill for review scope, edits, scoring, reporting, and when to stop. If council is unavailable, report the missing dependency.

Keep reviewers across rounds while they are available. Replace an unavailable reviewer with an eligible unused model from the council fallback order. The replacement counts toward the target once it independently scores the current screenshots. Record that score under the replacement's model identity.

Inspect the app's run instructions and working-tree state. Keep requested edits isolated from unrelated changes. Choose a screen/state inventory that covers the app's primary tasks, relevant loading/empty/error states, and the interactions the design depends on. Include desktop and mobile where supported.

If the user supplies screenshots of apps they admire, include them in every relevant review packet. Ask reviewers to compare useful aspects of hierarchy, density, navigation, and visual treatment while respecting this app's purpose. References are optional; do not wait for them when none were provided.

## Capture the baseline

Run the actual app and capture screenshots before UI edits. If a startup repair is needed, record it and distinguish the repaired baseline from the original state.

Use synthetic data when available. Keep viewport, scenario, and data consistent for before/after comparisons. Save screenshots outside the repository unless committed artifacts are requested. Inspect them yourself: settled screens, readable captures, and accurate state labels matter. Capture loading states intentionally rather than presenting them as completed screens.

## Review and improve

Give each member the same screenshots, relevant reference images, app purpose, and state descriptions. Have members inspect the images independently before seeing others' findings or scores. Keep reviews read-only. Use a frozen checkout or finish the round before editing what reviewers are inspecting.

Ask each member for:

- A 1–10 overall design score, grounded in the supplied evidence.
- Specific issues, naming the screen/state and user impact.
- The highest-value changes and any regressions.
- Limits of the evidence, particularly interactions screenshots cannot establish.

A 9 means a polished, coherent experience for the reviewed tasks with no material usability issue in the evidence. Minor preferences can remain. Do not ask reviewers to approve, round scores upward, or give a predetermined number.

Consolidate findings against the captured evidence. Reproduce material findings in the running app when they depend on interaction or the screenshots are inconclusive. If the user requested improvements, implement the most useful changes within scope. Explain declined suggestions when they would reduce usability, undo existing functionality, or expand the task unnecessarily.

Exercise changed interactions in the browser or native app, including keyboard and touch paths where relevant. Screenshots do not prove navigation, focus, validation, loading behavior, or successful application of changes. Run the project's relevant checks during iteration and final checks before completion.

Capture fresh screenshots after each implementation pass and request a new independent review from the current roster. Include changed screens, important states, and enough unchanged context to detect regressions. Never present old screenshots or old scores as evidence for a newer design.

## Continue until the gate passes

Continue implementing and reviewing until all required members score the same current design at or above the target and material functionality regressions are resolved. Do not stop just because most reviewers pass or a preset number of rounds has elapsed.

If a member remains below the target, request concrete remaining issues rather than a higher score. If progress stalls, re-examine the design approach instead of accumulating cosmetic changes. If a required review remains unfilled after fallbacks or required validation is unavailable, preserve the work and report why the target remains unmet. Honor a user instruction to stop or change scope.

## Ship on explicit request

Treat commit, push, PR creation, and merge as separate actions. Perform each only when the user has explicitly authorized it. An explicit full-send request authorizes the workflow in the [full-send skill](../full-send/SKILL.md), including its review, proof, and merge requirements.

For an authorized PR, include shareable before and after screenshots, each round's scores and changes, final validation results, and reviewer identities. If PR revisions materially change the UI or UX, capture fresh screenshots and repeat the council review before shipping.

## Show the work

Keep a round ledger with reviewer/model identity, actual scores, findings acted on or declined, main changes, screenshot paths, and validation results. Missing scores remain `no score`.

Show the user the scores, findings, and main changes from each round. Include representative screenshots, relevant reference comparisons, validation evidence, and any remaining limitations. Include the PR link and merge commit when those actions were authorized and completed.
