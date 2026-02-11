#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

pass() {
  echo "[OK]   $1"
}

if [[ ! -f CHANGELOG.md ]]; then
  fail "CHANGELOG.md missing"
fi
pass "CHANGELOG.md exists"

if ! grep -q '^## \[Unreleased\]' CHANGELOG.md; then
  fail "CHANGELOG.md has no [Unreleased] section"
fi
pass "CHANGELOG.md has [Unreleased]"

if [[ -f pyproject.toml ]] && awk '
  /^\[project\]/ {in_project=1; next}
  /^\[/ && in_project {in_project=0}
  in_project && /^version *= *"[^"]+"/ {found=1}
  END {exit(found ? 0 : 1)}
' pyproject.toml; then
  pass "pyproject.toml [project].version found"
elif [[ -f VERSION ]]; then
  pass "VERSION file found"
else
  fail "No version source (pyproject.toml [project].version or VERSION)"
fi

if [[ -f AGENTS.md ]]; then
  if grep -q 'BEGIN MDI VERSION POLICY' AGENTS.md; then
    pass "AGENTS.md includes MDI version policy block"
  else
    fail "AGENTS.md exists but has no MDI policy block"
  fi
else
  fail "AGENTS.md missing"
fi

echo "Release checks passed."
