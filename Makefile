.PHONY: test
test:
	pipenv run python manage.py test

.PHONY: test-coverage
test-coverage:
	./run_tests.sh

.PHONY: migrate
migrate:
	pipenv run python manage.py migrate

.PHONY: migrations
migrations:
	pipenv run python manage.py makemigrations

.PHONY: run
run:
	pipenv run python manage.py runserver

.PHONY: shell
shell:
	pipenv run python manage.py shell
