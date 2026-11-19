---
name: council
description: Trigger this if the user says 'council'.
---

# Council

Before an audit, address outstanding PR comments, fix known issues, and run
relevant checks. Give council the updated implementation; do not defer known
fixes until reviews return. If the user wants to discard the implementation
and explore new ideas, skip fixes to code being replaced.

Bring in three delegates for review or feedback. Use any council members the user specifies. Otherwise, use the default roster below.

- Claude Fable 5.2 at medium reasoning effort
- GPT Astra 6.2 at medium reasoning effort
- Muse Wonder Full (`muse-wonder-full-1.0`)

If a member is unavailable, try these fallbacks in order.

1. GPT Sol 6.2 at extra-high reasoning effort
2. Claude Opus 5.5 at high reasoning effort
3. GPT Terra 6.1 at extra-high reasoning effort

After these fallbacks, consider other models the harness lets you select explicitly.

Before launching anyone, resolve candidates against the harness's available
models and reserve a distinct canonical model ID for each reviewer in one
coordinator-owned roster. Aliases, reasoning settings, reviewer names and
different prompts do not make the same model distinct. Select replacements
from that roster centrally; delegates do not independently choose fallbacks.

In T3 Code, use `orchestrator_capabilities` to resolve IDs and `delegate_task`
to launch the reserved models in parallel. Elsewhere, use the harness's
subagent tools with an explicit model selection for every reviewer. If model
overrides require a fresh context, pass the task and evidence explicitly.
Never fill a slot with an inherited, default or unknown model. Check returned
model metadata against the reservation. When metadata is absent, use the
explicit selection accepted by the tool, not the delegate's self-description.
A reported substitution must pass the same uniqueness check before its review
counts; an unknown identity cannot count as a distinct council member.

Keep model reservations through retries and later rounds. A reviewer may reuse
its own model, but another reviewer cannot take that model, even after failure
or retirement. Replace a failed reviewer only with an unused, supported model;
record the replacement separately and do not carry over its predecessor's scores.
If distinct candidates run out, continue with fewer reviewers and report the
shortfall. Do not duplicate a model to reach three members or a score target,
and do not claim full-council approval while a required member is missing.
Report actual model IDs, substitutions and unfilled slots with the results.

Give each delegate the request and relevant context. For review or feedback,
keep their work read-only. Collect their responses and summarize the useful
findings, disagreements, and recommended next steps.

Do not wait idle. When a result arrives, check its findings against the code
at once and decide what to fix while the other delegates run. Do not edit
files while a delegate still reviews the same checkout. If the user's
instructions mark a delegate as non-blocking, do not wait for it; treat a
late result as feedback and do not record its score.

For a code review, ask each delegate for a score out of 10.
Count each full review pass as one round.
A fresh review after fixes starts a new round.

If the work ends in a pull request, put the results in the PR description.
Put this section before the model and harness line at the end:

```markdown
## Council review

Rounds: 2

| Delegate | Round 1 | Round 2 |
| --- | --- | --- |
| Claude Fable 5.2 | 7/10 | 9/10 |
| GPT Astra 6.2 | 8/10 | 10/10 |
| Muse Wonder Full | 7/10 | 9/10 |
```

If a delegate gives no score, write `no score`. Do not invent one.
If the PR is open, edit the description. Do not post a comment for this.
If there is no PR, put the same results in the final reply only.

If you agree with their recommendations, make the changes and request a fresh
review after. Continue this process until all delegates are satisfied with the
outcome.

Do not let repeated reviews result in scope creep. It is your job to fight to
keep scope limited.
