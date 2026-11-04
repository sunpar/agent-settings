#!/usr/bin/env bash
set -eu
rm -rf repo remote.git
git init -q --bare -b main remote.git
git init -q -b main repo
cd repo
git config user.email t@example.com; git config user.name Test
mkdir -p utils tests
printf 'def parse_date(s):\n    return s\n' > utils/dates.py
printf 'def test_x():\n    pass\n' > tests/test_dates.py
git add -A; git commit -qm "Initial"
git remote add origin ../remote.git; git push -qu origin main
git switch -qc fix-iso-z
printf 'from datetime import datetime\n\ndef parse_date(s):\n    return datetime.fromisoformat(s.replace("Z", "+00:00"))\n' > utils/dates.py
printf 'from utils.dates import parse_date\n\ndef test_x():\n    pass\n\ndef test_parse_date_zulu():\n    assert parse_date("2026-01-01T00:00:00Z").tzinfo is not None\n' > tests/test_dates.py
git commit -qam "Accept Z suffix in parse_date"
git push -qu origin fix-iso-z
# simulate a squash merge on the remote, then branch deletion
git switch -q main
git merge -q --squash fix-iso-z; git commit -qm "Accept Z suffix in parse_date (#412)"
git push -q origin main
git push -q origin --delete fix-iso-z
git fetch -q --prune
git switch -q fix-iso-z
