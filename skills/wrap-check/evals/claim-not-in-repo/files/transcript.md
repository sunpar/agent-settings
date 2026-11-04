# Session transcript: "Fix ISO date parsing"

**User:** `parse_date` in `utils/dates.py` chokes on ISO strings with a `Z` suffix. Fix it and add a test.

**Assistant:** Found it: `datetime.fromisoformat` on 3.10 doesn't accept `Z`. Replaced it with a normalisation step that maps `Z` to `+00:00`. Added `test_parse_date_zulu` in `tests/test_dates.py`. `uv run pytest tests/test_dates.py` passes (6 passed). Committed as "Accept Z suffix in parse_date" on branch `fix-iso-z`.

Task list: [x] Reproduce  [x] Fix parse_date  [x] Add test  [x] Run tests

**User:** great, push and open a PR

**Assistant:** Pushed `fix-iso-z` and opened https://github.com/acme/ledger/pull/412. CI is running.

**User:** CI is green, merge it

**Assistant:** Merged #412 (squash) into `main`. Branch `fix-iso-z` deleted on the remote. Nothing else is pending from my side.

**User:** /wrap-check
