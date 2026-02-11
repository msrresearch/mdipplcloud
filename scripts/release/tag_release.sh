#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$branch" != "main" ]]; then
  echo "Release tags must be created from main. Current branch: $branch" >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean. Commit/stash before tagging." >&2
  exit 1
fi

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
    echo "No version source found (pyproject.toml [project].version or VERSION)." >&2
    exit 1
  fi
}

version="$(get_version)"
tag="v${version}"

if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
  echo "Tag already exists: $tag" >&2
  exit 1
fi

git tag -a "$tag" -m "Release $tag"
echo "Created tag: $tag"
echo "Next: git push origin main --tags"
