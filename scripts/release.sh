#!/usr/bin/env bash
# Next release version and tag. This script never pushes.
#
# Versions look like YEAR.MONTH.NUMBER, for example 2026.10.3. The tag is the
# version with a "v": v2026.10.3. The month has no leading zero.
#
# Usage:
#   scripts/release.sh        same as "next"
#   scripts/release.sh next   print the next tag
#   scripts/release.sh bump   write the next version into the version files
#   scripts/release.sh tag    create the next tag on this clone, after checks
#
# Rule for the next version: take the highest tag. If its year and month are
# the current year and month, add 1 to the last number. Otherwise start the
# current month at 1.
#
# Release steps:
#   1. scripts/release.sh bump      then commit, with the changelog, in a PR
#   2. Merge the PR, then update master in this clone
#   3. scripts/release.sh tag       creates the tag here only
#   4. git push origin <tag>        you push it, the script does not
#
# Test option: RELEASE_TODAY=YYYY-MM-DD uses that date instead of today.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
cmd="${1:-next}"

die() { echo "error: $*" >&2; exit 1; }
note() { echo "$*" >&2; }

# The files with the version: the frontend or the backend.
if [ -f package.json ]; then
  VERSION_FILES="package.json"
elif [ -f pyproject.toml ]; then
  VERSION_FILES="pyproject.toml ksg_nett/settings.py"
else
  die "no package.json or pyproject.toml here"
fi

read_version() {
  case "$1" in
    package.json)
      sed -n 's/^[[:space:]]*"version":[[:space:]]*"\([^"]*\)".*/\1/p' "$1" | head -1 ;;
    pyproject.toml)
      sed -n 's/^version = "\([^"]*\)".*/\1/p' "$1" | head -1 ;;
    ksg_nett/settings.py)
      sed -n 's/^VERSION = "\([^"]*\)".*/\1/p' "$1" | head -1 ;;
  esac
}

write_version() {
  local file="$1" version="$2" tmp
  tmp="$(mktemp)"
  case "$file" in
    package.json)
      awk -v v="$version" '!d && /^[[:space:]]*"version":/ { sub(/"version":[[:space:]]*"[^"]*"/, "\"version\": \"" v "\""); d=1 } { print }' "$file" > "$tmp" ;;
    pyproject.toml)
      awk -v v="$version" '!d && /^version = "/ { $0 = "version = \"" v "\""; d=1 } { print }' "$file" > "$tmp" ;;
    ksg_nett/settings.py)
      awk -v v="$version" '!d && /^VERSION = "/ { $0 = "VERSION = \"" v "\""; d=1 } { print }' "$file" > "$tmp" ;;
  esac
  cat "$tmp" > "$file"
  rm -f "$tmp"
}

today="${RELEASE_TODAY:-$(date +%Y-%m-%d)}"
year="${today%%-*}"
month="$((10#$(echo "$today" | cut -d- -f2)))"

# Tags of the remote count too. A failed fetch is a warning, not an error.
git fetch --tags --quiet origin 2>/dev/null || note "warning: could not fetch tags from origin"

# The highest tag that looks like vYEAR.MONTH.NUMBER, by number, not by text.
latest="$(git tag --list 'v*' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' \
  | sed 's/^v//' \
  | awk -F. '{ printf "%d %d %d %s\n", $1, $2, $3, $0 }' \
  | sort -k1,1n -k2,2n -k3,3n | tail -1 | cut -d' ' -f4 || true)"

if [ -z "$latest" ]; then
  next="$year.$month.1"
else
  ly="$(echo "$latest" | cut -d. -f1)"
  lm="$(echo "$latest" | cut -d. -f2)"
  ln="$(echo "$latest" | cut -d. -f3)"
  if [ "$ly" = "$year" ] && [ "$lm" = "$month" ]; then
    next="$year.$month.$((ln + 1))"
  elif [ "$ly" -gt "$year" ] || { [ "$ly" = "$year" ] && [ "$lm" -gt "$month" ]; }; then
    note "warning: the latest tag v$latest is after $today. Continuing from it."
    next="$ly.$lm.$((ln + 1))"
  else
    next="$year.$month.1"
  fi
fi

case "$cmd" in
  next)
    if [ -n "$latest" ]; then label="v$latest"; else label="none"; fi
    note "latest tag: $label  ->  next: v$next"
    echo "v$next"
    ;;

  bump)
    for f in $VERSION_FILES; do
      write_version "$f" "$next"
      [ "$(read_version "$f")" = "$next" ] || die "could not set the version in $f"
      note "set $f to $next"
    done
    note ""
    note "Commit this with the changelog in a pull request. After the merge,"
    note "update master in this clone and run: scripts/release.sh tag"
    echo "v$next"
    ;;

  tag)
    branch="$(git branch --show-current)"
    [ "$branch" = "master" ] || die "you are on '$branch'. Switch to master first."
    [ -z "$(git status --porcelain --untracked-files=no)" ] || die "uncommitted changes in tracked files"
    git fetch --quiet origin master || die "could not fetch origin/master"
    [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/master)" ] \
      || die "master is not the same as origin/master. Update master first."
    first_file="${VERSION_FILES%% *}"
    in_files="$(read_version "$first_file")"
    if git rev-parse -q --verify "refs/tags/v$in_files" >/dev/null; then
      die "tag v$in_files already exists. Push it with: git push origin v$in_files"
    fi
    for f in $VERSION_FILES; do
      have="$(read_version "$f")"
      [ "$have" = "$next" ] || die "$f has version '$have', but the next release is '$next'. Run 'scripts/release.sh bump' and merge it first."
    done
    if [ -f CHANGELOG.md ] && ! grep -qE "^## \[v?$next\]" CHANGELOG.md; then
      note "warning: CHANGELOG.md has no section for $next"
    fi
    git tag -a "v$next" -m "Release $next"
    note "created tag v$next on $(git rev-parse --short HEAD). It is NOT pushed."
    note "Push it with: git push origin v$next"
    echo "v$next"
    ;;

  *)
    die "unknown command '$cmd'. Use next, bump or tag."
    ;;
esac
