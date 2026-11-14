#!/usr/bin/env bash
# Fails when a real-looking secret is tracked (or untracked and not ignored) in the repo.
#   scripts/check_secrets.sh            working tree: tracked + untracked files, minus .gitignore
#   scripts/check_secrets.sh --history  also every added line in all commits
# Dummies such as sk_test_dummy, whsec_dummy and sk-ant-test-not-real are shorter than the
# thresholds below and pass; real keys are far longer.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

PATTERN='sk_(live|test)_[A-Za-z0-9]{20,}|rk_(live|test)_[A-Za-z0-9]{20,}|pk_live_[A-Za-z0-9]{10,}|whsec_[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9_-]{20,}'
SELF=':!scripts/check_secrets.sh'
status=0

if git grep --untracked -nIE "$PATTERN" -- . "$SELF"; then
  echo "check_secrets: secret-looking value in the working tree" >&2
  status=1
fi

if git ls-files --cached | grep -Eq '(^|/)\.env($|\.[a-z]+$)' &&
  git ls-files --cached | grep -E '(^|/)\.env($|\.[a-z]+$)' | grep -vq '\.env\.example$'; then
  echo "check_secrets: a .env file is tracked" >&2
  status=1
fi

if [ "${1:-}" = "--history" ]; then
  if git log --all -p --no-color -G "$PATTERN" -- . "$SELF" | grep -E '^\+' | grep -E "$PATTERN"; then
    echo "check_secrets: secret-looking value in git history" >&2
    status=1
  fi
fi

[ "$status" -eq 0 ] && echo "check_secrets: ok"
exit "$status"
