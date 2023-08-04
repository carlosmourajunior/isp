SHELL:=/bin/bash
ARGS = $(filter-out $@,$(MAKECMDGOALS))
MAKEFLAGS += --silent
BASE_PATH=${PWD}
PYTHON_EXEC=python
DOCKER_COMPOSE_FILE=$(shell echo -f docker-compose.yml)

show_env:
	# Show wich DOCKER_COMPOSE_FILE and ENV the recipes will user
	# It should be referenced by all other recipes you want it to show.
	# It's only printed once even when more than a recipe executed uses it
	sh -c "if [ \"${ENV_PRINTED:-0}\" != \"1\" ]; \
	then \
		echo DOCKER_COMPOSE_FILE = \"${DOCKER_COMPOSE_FILE}\"; \
		echo OSFLAG = \"${OSFLAG}\"; \
	fi; \
	ENV_PRINTED=1;"

_rebuild: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} down
	docker-compose ${DOCKER_COMPOSE_FILE} build --no-cache --force-rm

up: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} up -d --remove-orphans

# up_debug: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} stop app
# 	docker-compose ${DOCKER_COMPOSE_FILE} -f docker-compose.override.debug.yml up -d --remove-orphans

log: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} logs -f --tail 200 app

logs: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} logs -f --tail 200

stop: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} stop

status: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} ps

restart: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} restart

sh: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec ${ARGS} bash

# psql: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec db psql -d database

# pgcli: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app pgcli postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}

# _drop_db:
# 	docker-compose ${DOCKER_COMPOSE_FILE} stop db
# 	docker-compose ${DOCKER_COMPOSE_FILE} rm db

# _create_db:
# 	docker-compose ${DOCKER_COMPOSE_FILE} up -d db

# recreate_db: show_env _drop_db _create_db

createsuperuser: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} ./manage.py shell -c "from apps.user.models import User; User.objects.create_superuser('root@root.com.br', 'root', name='root'); print('Superuser created: root@root.com.br:root')"

# fixtures: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app pytest --fixtures

# migrate: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py migrate ${ARGS}

# der_dot: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py graph_models -a -I Category,Obligation,ObligationDocuments -o vert-ofiscais-der.dot

# collectstatic: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py collectstatic --no-input

makemigrations: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py makemigrations ${ARGS}
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py migrate


# makemigrations__merge: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py makemigrations --merge
#   docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py migrate

migrate: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py migrate

# pip_install: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} -m pip install -r requirements.txt

manage: show_env
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py ${ARGS}

# test-watch: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app pytest --testmon "${ARGS}"

# coverage: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app pytest --cov --cov-report xml:coverage.xml
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app coverage html
# 	sudo chown -R "${USER}:${USER}" ./src/htmlcov

# clean_db: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec db psql -d ${POSTGRES_DB} -c 'drop schema public cascade; create schema public;'

# showmigrations: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py showmigrations ${ARGS}

# restartq: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} stop djangoq
# 	docker-compose ${DOCKER_COMPOSE_FILE} up -d djangoq

chown_project:
	sudo chown -R "${USER}:${USER}" ./

# generate_factories_bot: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} manage.py generate_factories

# generate_factories: show_env generate_factories_bot chown_project flake8

# create_venv: show_env
# 	sudo apt-get install python3-dev python3-wheel python-dev gcc libpq-dev -y
# 	python3 -m venv ${VENV_PATH}
# 	${VENV_PATH}/bin/python -m pip install --upgrade pip setuptools wheel
# 	${VENV_PATH}/bin/pip install -r ./src/requirements.txt

# upgrade_packages: show_env pip_install
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app pip-upgrade --skip-virtualenv-check

# restore_data_local: show_env clean_db
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec db sh -c "PGPASSWORD=${POSTGRES_PASSWORD} psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -h ${POSTGRES_HOST} -p ${POSTGRES_PORT} -f /db/backup.sql"

shell_plus:
	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} ./manage.py shell_plus

# kafka_consumer: show_env
# 	docker-compose ${DOCKER_COMPOSE_FILE} exec app ${PYTHON_EXEC} ./manage.py kafka_consumer