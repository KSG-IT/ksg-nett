#!/usr/bin/env bash
# Next release tag, and the release itself. A release is only a tag on master.
# Nothing is edited or committed. CI reads the version from the tag.
#
# Versions look like YEAR.MONTH.NUMBER, for example 2026.10.3. The tag is the
# version with a "v": v2026.10.3. The month has no leading zero.
#
# Usage:
#   scripts/release.sh          same as "next"
#   scripts/release.sh next     print the next tag
#   scripts/release.sh release  show what ships, ask, then create and push the tag
#
# Rule for the next version: take the highest tag. If its year and month are
# the current year and month, add 1 to the last number. Otherwise start the
# current month at 1.
#
# With make: make release-version (preview) and make release.
#
# After the push, approve the run in GitHub Actions. Then CI deploys, and
# creates the GitHub release with notes from the merged pull requests.
#
# Test options: RELEASE_TODAY=YYYY-MM-DD uses that date instead of today.
# RELEASE_YES=1 skips the question. RELEASE_NO_PUSH=1 creates the tag only.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
cmd="${1:-next}"

die() { echo "error: $*" >&2; exit 1; }
note() { echo "$*" >&2; }

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

  release)
    branch="$(git branch --show-current)"
    [ "$branch" = "master" ] || die "you are on '$branch'. Switch to master first."
    [ -z "$(git status --porcelain --untracked-files=no)" ] || die "uncommitted changes in tracked files"
    git fetch --quiet origin master || die "could not fetch origin/master"
    [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/master)" ] \
      || die "master is not the same as origin/master. Update master first."
    git rev-parse -q --verify "refs/tags/v$next" >/dev/null && die "tag v$next already exists"

    if [ -n "$latest" ]; then
      range="v$latest..HEAD"
      count="$(git rev-list --first-parent --count "$range")"
      [ "$count" -gt 0 ] || die "nothing new since v$latest"
      note "Shipping $count merged changes since v$latest:"
      git log --first-parent --format='  %h %s' "$range" >&2
    else
      note "First release tag. Shipping everything on master."
    fi
    note ""
    note "release: v$next  at  $(git log -1 --format='%h %s')"
    note "Pushing the tag starts the release workflow. You approve it in GitHub Actions."
    if [ "${RELEASE_YES:-}" != "1" ]; then
      printf 'Type the tag name to release it: ' >&2
      read -r answer
      [ "$answer" = "v$next" ] || die "not confirmed. Nothing was done."
    fi
    git tag -a "v$next" -m "Release $next"
    if [ "${RELEASE_NO_PUSH:-}" = "1" ]; then
      note "created tag v$next. It is NOT pushed."
    else
      git push origin "refs/tags/v$next" || { git tag -d "v$next" >/dev/null; die "push failed. The local tag is removed."; }
      note "pushed v$next. Approve the run in GitHub Actions."
    fi
    echo "v$next"
    ;;

  *)
    die "unknown command '$cmd'. Use next or release."
    ;;
esac
