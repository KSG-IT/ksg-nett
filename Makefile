.PHONY: test
test:
	poetry run py.test

.PHONY: test-coverage
test-coverage:
	./run_tests.sh

.PHONY: migrate
migrate:
	poetry run python manage.py migrate

.PHONY: migrations
migrations:
	poetry run python manage.py makemigrations

.PHONY: run
run:
	poetry run python manage.py runserver

.PHONY: shell
shell:
	poetry run python manage.py shell

.PHONY: user
user:
	poetry run python manage.py createsuperuser

.PHONY: showmigrations
showmigrations:
	poetry run python manage.py showmigrations

.PHONY: testdata
testdata:
	poetry run python manage.py generate_testdata


.PHONY: activeadmission
activeadmission:
	poetry run python manage.py generate_active_admission


.PHONY: nukeadmission
nukeadmission:
	poetry run python manage.py nuke_admission_data


.PHONY: debt
debt:
	poetry run python manage.py debtcollection

.PHONY: alldebt
alldebt:
	poetry run python manage.py debtcollection --all-users

.PHONY: stripe
stripe:
	stripe listen --forward-to localhost:8000/economy/stripe-webhook

.PHONY: release-version
# Next release tag. ACTION=bump writes the version files, ACTION=tag creates the tag here.
release-version:
	@scripts/release.sh $(ACTION)

.PHONY: push-release
# Pushes the newest tag that origin does not have, after you type its name.
push-release:
	@scripts/release.sh push
