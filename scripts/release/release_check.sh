#!/usr/bin/env bash
set -euo pipefail

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "[FAIL] release-check requires a git repository" >&2
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

pass() {
  echo "[OK]   $1"
}

warn() {
  echo "[WARN] $1"
}

get_version() {
  if [[ -f pyproject.toml ]] && awk '
    /^\[project\]/ {in_project=1; next}
    /^\[/ && in_project {in_project=0}
    in_project && /^version *= *"[^"]+"/ {found=1}
    END {exit(found ? 0 : 1)}
  ' pyproject.toml; then
    awk '
      /^\[project\]/ {in_project=1; next}
      /^\[/ && in_project {in_project=0}
      in_project && /^version *= *"[^"]+"/ {
        gsub(/^[^\"]*\"/, "", $0)
        gsub(/\".*$/, "", $0)
        print $0
        exit
      }
    ' pyproject.toml
  elif [[ -f VERSION ]]; then
    tr -d '[:space:]' < VERSION
  else
    return 1
  fi
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

if ! git remote get-url origin >/dev/null 2>&1; then
  fail "origin remote missing; cannot verify remote tag state"
fi
pass "origin remote configured"

version="$(get_version)"
tag="v${version}"
head_commit="$(git rev-parse HEAD)"

if ! remote_tag_lines="$(git ls-remote --tags origin "$tag" "$tag^{}" 2>/dev/null)"; then
  fail "failed to query tags from origin; cannot verify whether this version is already published"
fi
pass "origin tags queried"

remote_tag_commit="$(printf '%s\n' "$remote_tag_lines" | awk -v tag="$tag" '
  $2 == ("refs/tags/" tag "^{}") {print $1; found=1; exit}
  $2 == ("refs/tags/" tag) {direct=$1}
  END {
    if (!found && direct != "") {
      print direct
    }
  }
')"

if [[ -n "$remote_tag_commit" ]]; then
  if [[ "$remote_tag_commit" == "$head_commit" ]]; then
    pass "Version tag $tag already points at HEAD on origin"
  else
    fail "Version tag $tag already exists on a different commit on origin; bump version before preparing a new release"
  fi
else
  pass "Version $version is not already tagged on origin"
fi

if [[ -f AGENTS.md ]]; then
  if grep -q 'BEGIN MDI VERSION POLICY' AGENTS.md; then
    pass "AGENTS.md includes MDI version policy block"
  else
    fail "AGENTS.md exists but has no MDI policy block"
  fi
else
  warn "AGENTS.md missing (expected on local/dev; release branches may omit planning files)"
fi

echo "Release checks passed."
