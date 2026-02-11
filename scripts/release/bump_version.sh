#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: bump_version.sh [patch|minor|major]"
}

part="${1:-}"
if [[ -z "$part" ]]; then
  usage
  exit 1
fi
if [[ "$part" != "patch" && "$part" != "minor" && "$part" != "major" ]]; then
  usage
  exit 1
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

detect_version_mode() {
  if [[ -f pyproject.toml ]] && awk '
    /^\[project\]/ {in_project=1; next}
    /^\[/ && in_project {in_project=0}
    in_project && /^version *= *"[^"]+"/ {found=1}
    END {exit(found ? 0 : 1)}
  ' pyproject.toml; then
    echo "pyproject"
  else
    echo "version_file"
  fi
}

current_version_from_pyproject() {
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
}

current_version_from_file() {
  if [[ ! -f VERSION ]]; then
    echo "0.1.0" > VERSION
  fi
  tr -d '[:space:]' < VERSION
}

increment_semver() {
  local version="$1"
  local part="$2"

  if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Version is not plain SemVer (X.Y.Z): $version" >&2
    exit 1
  fi

  local major minor patch
  IFS='.' read -r major minor patch <<< "$version"

  case "$part" in
    patch)
      patch=$((patch + 1))
      ;;
    minor)
      minor=$((minor + 1))
      patch=0
      ;;
    major)
      major=$((major + 1))
      minor=0
      patch=0
      ;;
  esac

  echo "${major}.${minor}.${patch}"
}

update_pyproject_version() {
  local next_version="$1"
  local tmp
  tmp="$(mktemp)"

  awk -v nv="$next_version" '
    BEGIN {in_project=0; done=0}
    {
      if ($0 ~ /^\[project\]/) {
        in_project=1
        print $0
        next
      }
      if ($0 ~ /^\[/ && in_project) {
        in_project=0
      }
      if (in_project && !done && $0 ~ /^version *= *"[^"]+"/) {
        sub(/"[^"]+"/, "\"" nv "\"")
        done=1
      }
      print $0
    }
    END {
      if (!done) exit 2
    }
  ' pyproject.toml > "$tmp"

  mv "$tmp" pyproject.toml
}

update_changelog() {
  local next_version="$1"
  local today
  today="$(date +%Y-%m-%d)"

  if [[ ! -f CHANGELOG.md ]] || [[ ! -s CHANGELOG.md ]]; then
    cat > CHANGELOG.md <<'CHANGELOG'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

### Added
- 

### Changed
- 

### Fixed
- 
CHANGELOG
  fi

  if grep -q "^## \[$next_version\]" CHANGELOG.md; then
    return
  fi

  local tmp
  tmp="$(mktemp)"

  awk -v next="$next_version" -v d="$today" '
    BEGIN {inserted=0}
    {
      print $0
      if (!inserted && $0 ~ /^## \[Unreleased\]/) {
        print ""
        print "## [" next "] - " d
        print ""
        print "### Added"
        print "- "
        print ""
        print "### Changed"
        print "- "
        print ""
        print "### Fixed"
        print "- "
        inserted=1
      }
    }
  ' CHANGELOG.md > "$tmp"

  mv "$tmp" CHANGELOG.md
}

mode="$(detect_version_mode)"
if [[ "$mode" == "pyproject" ]]; then
  current="$(current_version_from_pyproject)"
else
  current="$(current_version_from_file)"
fi

next="$(increment_semver "$current" "$part")"

if [[ "$mode" == "pyproject" ]]; then
  update_pyproject_version "$next"
else
  printf "%s\n" "$next" > VERSION
fi

update_changelog "$next"

echo "Version bumped: $current -> $next"
echo "Remember to fill changelog entries for $next."
