.PHONY: test
test:
	python manage.py test

.PHONY: test-coverage
test-coverage:
	./run_tests.sh

.PHONY: migrate
migrate:
	python manage.py migrate

.PHONY: migrations
migrations:
	python manage.py makemigrations

.PHONY: run
run:
	python manage.py runserver

.PHONY: shell
shell:
	python manage.py shell
