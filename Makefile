.PHONY: test
test:
	python manage.py test

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
