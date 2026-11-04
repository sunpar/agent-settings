#!/usr/bin/env bash
set -eu
rm -rf repo remote.git
git init -q --bare -b main remote.git
git init -q -b main repo
cd repo
git config user.email t@example.com; git config user.name Test
mkdir -p exports reports
printf 'from net import legacy_fetch\n' > exports/run.py
printf 'from net import legacy_fetch\n' > reports/run.py
printf '# Changelog\n\n## Unreleased\n' > CHANGELOG.md
git add -A; git commit -qm "Initial"
git remote add origin ../remote.git; git push -qu origin main
git switch -qc exports-fetch-v2
printf 'from net import fetch_v2\n' > exports/run.py
git commit -qam "Move exports to fetch_v2"
git push -qu origin exports-fetch-v2
