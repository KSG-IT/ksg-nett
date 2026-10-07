# Release procedure

A release is a tag on `master`. Nothing is edited or committed to make one. The backend deploys by hand on cirkus, from the tag.

## 1. Tag
1. `git checkout master && git pull`
2. `make release-preview` prints the next tag. It changes nothing.
3. `make release` lists the merged PRs since the last tag. Type the tag name to confirm. It creates the tag and pushes it.

The tag starts `.github/workflows/release.yml`. It checks that the tag is on `master` and creates the GitHub Release with notes from the merged PRs. It does not deploy.

Tags are versions in the form `v<year>.<month>.<number>`, for example `v2026.10.4`. Only an admin can create a tag, and a tag cannot be moved or deleted.

## 2. Deploy on cirkus
Do this in the instance directory, with the virtualenv active. Run `loadenv` first. It loads the environment and the `.env` variables, which `migrate` needs.

1. `git fetch --tags`
2. Note what is deployed now: `git describe --tags`
3. `git checkout <tag>`
4. Dependencies: check if `pyproject.toml` or `poetry.lock` changed with `git diff <old tag> <tag> --stat -- pyproject.toml poetry.lock`. If they did, install them with `python -m pip install .`. Use `python -m pip`, not `pip`: on cirkus `pip` is not the one of the virtualenv, so a plain `pip` installs to the wrong place.
5. Migrations: `python manage.py migrate --plan`. If it lists migrations, run `python manage.py migrate`.
6. `touch` the `touch-reload` file of the instance.
7. Read `/var/log/uwsgi/app/<name>.log`. The workers must start again with no traceback.

## Rules
- Deploy the backend before the frontend. A migration must be safe to run before the matching frontend is live.
- Some data migrations delete rows and cannot be reversed. Read the migrations of the release before you run them.
- Features that are not ready stay behind a feature flag, since every merge to `master` can go in the next release.

## Roll back
1. `git checkout <old tag>`
2. `touch` the `touch-reload` file.

A migration is not reversed by this. Check the release's migrations first, and restore a database backup if a migration must be undone.

## Hotfix
- If `master` is safe to ship, merge the fix to `master` and make a normal release.
- If `master` has work that is not ready, branch from the last tag with `git checkout -b hotfix/<name> <last tag>`. Fix, then tag the commit by hand and deploy that tag. Then cherry-pick the fix to `master` in a normal PR. The next release must have a higher version than the hotfix tag.
