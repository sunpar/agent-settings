# Deslop examples

Read the case that matches the candidate edit.

[Branch scope](#choose-the-comparison-for-a-stacked-pr), [local guard](#delete-a-guard-after-local-construction), [exception handling](#keep-a-fallback-attached-to-the-operation-it-covers), [default values](#simplify-a-default-and-preserve-zero), [type narrowing](#remove-a-cast-after-narrowing), [hidden callers](#trace-a-caller-or-side-effect-before-deleting-code), [clean diff](#accept-a-clean-diff)

## Choose the comparison for a stacked PR

**Given** The PR targets `origin/release/2.4-hotfix`. The remote default is
`origin/develop`, the topic tracks its published copy, and `reports.py` is
partially staged. An unrelated scratch file is untracked.

**Decision** Start at the PR target's merge base. Read all three diff layers
and use the current file contents to choose edits. If an unstaged change
already removed a committed line, leave it absent.

```bash
git --no-optional-locks status --short --untracked-files=all
git --no-optional-locks diff origin/release/2.4-hotfix...HEAD
git --no-optional-locks diff --cached
git --no-optional-locks -c diff.autoRefreshIndex=false diff
```

**Check** Confirm the final edits are in scope, the staged diff matches its
starting state, and the scratch file is untouched. The worktree comparison
disables Git's index stat refresh. [Git diff](https://git-scm.com/docs/git-diff#_description)

## Delete a guard after local construction

**Given** `parse_request(payload)` rejects malformed input. A legacy request
still takes a supported route. The current route contains this block.

```diff
 rows = []
-if rows is None:
-    rows = []
```

**Decision** Delete the check. The assignment creates a list on that path and
there is no intervening assignment. Keep the parser and legacy route.

**Check** Current and legacy requests still return their expected results.
Malformed input still raises the parser's error.

## Keep a fallback attached to the operation it covers

```python
def load_settings(path):
    try:
        text = path.read_text()
    except FileNotFoundError:
        return default_settings()
    return resolve_includes(text, path.parent)
```

**Decision** Leave `resolve_includes` outside the `try`. Only an absent
settings file uses defaults. An existing settings file can reference a missing
include, and widening the handler would silently use defaults for that case.

**Check** A missing settings file returns defaults. A missing include raises
`FileNotFoundError` for the include path. [Python exception handling](https://docs.python.org/3.11/tutorial/errors.html#handling-exceptions)

## Simplify a default and preserve zero

**Given** `retries` is a local `number | null | undefined`. Zero disables
retries. Missing values use a default computed on demand.

```diff
-const limit = retries === null || retries === undefined ? defaultRetries() : retries;
+const limit = retries ?? defaultRetries();
```

**Check** With `0`, the limit is zero and the default function is never
called. With either `null` or `undefined`, it is called once. A rewrite with
`||` fails the zero case. [TypeScript nullish coalescing](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-7.html#nullish-coalescing)

## Remove a cast after narrowing

**Given** `Job` is a union of an email job with `recipient` and an archive
job with `path`. The parser validates external data before returning a `Job`.

```diff
 if (job.kind === "email") {
-    return (job as any).recipient;
+    return job.recipient;
 }
```

**Decision** Remove the cast inside that branch. The `kind` check narrows the
type and the field access stays the same. Keep the external-data validation.

**Check** Run the type check and exercise both job variants. [TypeScript discriminated unions](https://www.typescriptlang.org/docs/handbook/2/narrowing.html#discriminated-unions)

## Trace a caller or side effect before deleting code

**Given** `reports.cli:main` has no direct callers, but `[project.scripts]`
declares it as a console command. `reports/__init__.py` imports `Report`
for callers using `from reports import Report`.

**Decision** Keep both names. The metadata and the public import path are
callers' contracts. Check those declarations before applying an unused-symbol
fix. [PyPA entry points](https://packaging.python.org/en/latest/specifications/pyproject-toml/#entry-points), [Ruff re-exports](https://docs.astral.sh/ruff/rules/unused-import/#why-is-this-bad)

**Check** Exercise the registered command and the public import. When two
helpers instead appear interchangeable, compare effects too. A helper that
writes an audit event requires an assertion on that event as well as its return
value.

## Remove a repeated lookup

**Given** An export loop reloads the same immutable options on each row.
The options depend only on the requested format. Existing behavior skips the
lookup for an empty export.

**Decision** Load the options once for a nonempty export. Keep the lookup
inside the operation so a later export can use a different format.

**Check** Assert the exported rows and count calls through the existing
entry point. Expect one lookup for multiple rows, zero for an empty export,
and a fresh lookup for the next export.

## Put a shared rule with its owner

**Given** A new caller compensates for a missing default in the response
builder. Every current caller uses the same documented default. External
input validation already rejects unsupported values before calling the
builder.

**Decision** Apply the default in the builder when that change fits the scope.
Leave input validation at the boundary. If another caller intentionally omits
the field, keep its behavior and report the ownership question separately.

**Check** Exercise the new caller and an existing caller with missing and
explicit values. Assert the actual response fields and keep the rejection
test for unsupported input.

## Accept a clean diff

**Given** The scoped change adds two tests that submit the same duplicate
charge. One asserts the rejection, and the other asserts that the stored row
count stays at one. A comment explains why retries must be idempotent.

**Decision** Leave the diff as it is. The repeated action checks separate
contracts, and the comment records why one of them matters. [Google code review guidance on tests](https://google.github.io/eng-practices/review/reviewer/looking-for.html#tests)

**Check** A rejected request that writes a second row must fail the persistence
assertion even when the rejection assertion passes. If the persistence check
requires a database that cannot start, report that check as blocked.
