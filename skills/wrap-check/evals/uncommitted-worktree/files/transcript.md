# Session transcript: "Rate limit the public API"

**User:** Add per-key rate limiting to the public API. 100 req/min, return 429 with a Retry-After header.

**Assistant:** Added a token-bucket limiter in `api/ratelimit.py` and wired it into `api/middleware.py`. Committed the limiter as "Add token bucket rate limiter".

**Assistant:** Wired the middleware and added `tests/test_ratelimit.py`. `uv run pytest tests/test_ratelimit.py` passes (4 passed). I haven't committed the middleware and test changes yet; I'll commit once you've had a look.

While I was in there: `client/http.py`'s retry loop ignores the `Retry-After` header and retries immediately, so our own SDK will hammer the new limit. That's a separate bug in a different package; worth its own PR.

**User:** looks good

**User:** ok i think we're done here, can i archive this?
