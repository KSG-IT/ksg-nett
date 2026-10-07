#!/usr/bin/env bash
# Next release tag, and the release itself. A release is only a tag on master.
# Nothing is edited or committed. CI reads the version from the tag.
#
# Versions look like YEAR.MONTH.NUMBER, for example 2026.10.3. The tag is the
# version with a "v": v2026.10.3. The month has no leading zero.
#
# Usage:
#   scripts/release.sh          same as "preview"
#   scripts/release.sh preview  print the next tag
#   scripts/release.sh release  show what ships, ask, then create and push the tag
#
# Rule for the next version: take the highest tag. If its year and month are
# the current year and month, add 1 to the last number. Otherwise start the
# current month at 1.
#
# With make: make release-preview and make release.
#
# After the push, CI creates the GitHub release with notes from the merged
# pull requests. The deploy on cirkus stays manual: the script prints the
# commands for it (see release_procedure.md).
#
# Test options: RELEASE_TODAY=YYYY-MM-DD uses that date instead of today.
# RELEASE_YES=1 skips the question. RELEASE_NO_PUSH=1 creates the tag only.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
cmd="${1:-preview}"

die() { echo "error: $*" >&2; exit 1; }
note() { echo "$*" >&2; }

# The commands to deploy tag $1 on cirkus, with notes on the dependencies and
# migrations that changed since tag $2 (empty for the first release).
deploy_steps() {
  local tag="$1" old="$2"
  note ""
  note "Deploy on cirkus, in the production instance directory, with the virtualenv active:"
  note "  loadenv"
  note "  git fetch --tags && git describe --tags   # the version that runs now"
  note "  git checkout $tag"
  if [ -z "$old" ] || ! git diff --quiet "$old" "$tag" -- pyproject.toml poetry.lock; then
    note "  python -m pip install .                   # dependencies changed"
  fi
  local migrations=""
  [ -n "$old" ] && migrations="$(git diff --name-only --diff-filter=A "$old" "$tag" -- '*/migrations/0*.py')"
  if [ -z "$old" ] || [ -n "$migrations" ]; then
    note "  python manage.py migrate --plan && python manage.py migrate"
    [ -n "$migrations" ] && echo "$migrations" | sed 's/^/      new: /' >&2
  fi
  note "  touch <the touch-reload file of the instance>"
  note "Then read /var/log/uwsgi/app/<name>.log. The workers must start with no traceback."
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
  preview)
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
    note "Pushing the tag starts the release workflow. It creates the GitHub release. It does not deploy."
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
      note "pushed v$next."
    fi
    deploy_steps "v$next" "${latest:+v$latest}"
    echo "v$next"
    ;;

  *)
    die "unknown command '$cmd'. Use preview or release."
    ;;
esac
