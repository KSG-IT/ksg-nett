DOCKER_COMPOSE_COMMAND = @docker-compose -f ./docker/docker-compose.yml
BACKEND_SERVICE_NAME = django

.PHONY: test
test:
	poetry run python manage.py test

.PHONY: test-coverage
test-coverage:
	./run_tests.sh

.PHONY: migrate
migrate:
	poetry run python manage.py migrate

.PHONY: migrate-cooler
migrate-cooler:
	docker run --rm ksg-nett poetry run python manage.py migrate

.PHONY: migrations
migrations:
	poetry run python manage.py makemigrations

.PHONY: migrations-cooler
makemigrations-cooler:
	docker run --rm ksg-nett poetry run python manage.py makemigrations

.PHONY: run
run:
	poetry run python manage.py runserver

.PHONY: shell
shell:
	poetry run python manage.py shell

.PHONY: user
user:
	poetry run python manage.py createsuperuser

.PHONY: user-cooler
user-cooler:
	docker run --rm ksg-nett poetry run python manage.py createsuperuser

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
