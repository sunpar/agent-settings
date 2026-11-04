#!/usr/bin/env bash
set -eu
rm -rf repo remote.git
git init -q --bare -b main remote.git
git init -q -b main repo
cd repo
git config user.email t@example.com; git config user.name Test
mkdir -p api tests client
printf 'def app(req):\n    return 200\n' > api/middleware.py
printf 'def get(url):\n    pass\n' > client/http.py
git add -A; git commit -qm "Initial"
git remote add origin ../remote.git; git push -qu origin main
git switch -qc rate-limit
git push -qu origin rate-limit
printf 'class TokenBucket:\n    def __init__(self, rate=100):\n        self.rate = rate\n' > api/ratelimit.py
git add -A; git commit -qm "Add token bucket rate limiter"
printf 'from api.ratelimit import TokenBucket\n\ndef app(req):\n    return 429\n' > api/middleware.py
printf 'def test_limit():\n    assert True\n' > tests/test_ratelimit.py
