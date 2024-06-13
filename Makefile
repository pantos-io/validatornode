PANTOS_VERSION := $(shell poetry version -s)
PANTOS_REVISION ?= 1
PANTOS_VALIDATOR_NODE_SSH_HOST ?= bdev-validator-node
PYTHON_FILES_WITHOUT_TESTS := pantos/validatornode linux/start-web-server
PYTHON_FILES := $(PYTHON_FILES_WITHOUT_TESTS) tests

.PHONY: dist
dist: tar wheel debian

.PHONY: code
code: check format lint sort bandit test

.PHONY: check
check:
	poetry run mypy $(PYTHON_FILES_WITHOUT_TESTS)
	poetry run mypy --explicit-package-bases tests

.PHONY: format
format:
	poetry run yapf --in-place --recursive $(PYTHON_FILES)

.PHONY: format-check
format-check:
	poetry run yapf --diff --recursive $(PYTHON_FILES)

.PHONY: lint
lint:
	poetry run flake8 $(PYTHON_FILES)

.PHONY: sort
sort:
	poetry run isort --force-single-line-imports $(PYTHON_FILES)

.PHONY: sort-check
sort-check:
	poetry run isort --force-single-line-imports $(PYTHON_FILES) --check-only

.PHONY: bandit
bandit:
	poetry run bandit -r $(PYTHON_FILES) --quiet --configfile=.bandit

.PHONY: bandit-check
bandit-check:
	poetry run bandit -r $(PYTHON_FILES) --configfile=.bandit

.PHONY: test
test:
	poetry run python3 -m pytest tests --ignore tests/database/postgres

.PHONY: test-postgres
test-postgres:
	poetry run python3 -m pytest tests/database/postgres

.PHONY: coverage
coverage:
	poetry run python3 -m pytest --cov-report term-missing --cov=pantos tests --ignore tests/database/postgres

.PHONY: coverage-postgres
coverage-postgres:
	poetry run python3 -m pytest --cov-report term-missing --cov=pantos tests/database/postgres

.PHONY: coverage-all
coverage-all:
	poetry run python3 -m pytest --cov-report term-missing --cov=pantos tests

.PHONY: tar
tar: dist/pantos_validator_node-$(PANTOS_VERSION).tar.gz

dist/pantos_validator_node-$(PANTOS_VERSION).tar.gz: pantos alembic.ini validator-node-config.yml validator-node-config.env pantos-validator-node.sh pantos-validator-node-worker.sh
	cp validator-node-config.yml pantos/validator-node-config.yml
	cp validator-node-config.env pantos/validator-node-config.env
	cp alembic.ini pantos/alembic.ini
	cp pantos-validator-node.sh pantos/pantos-validator-node.sh
	cp pantos-validator-node-worker.sh pantos/pantos-validator-node-worker.sh
	chmod 755 pantos/pantos-validator-node.sh
	chmod 755 pantos/pantos-validator-node-worker.sh
	poetry build -f sdist
	rm pantos/validator-node-config.yml
	rm pantos/validator-node-config.env
	rm pantos/alembic.ini
	rm pantos/pantos-validator-node.sh
	rm pantos/pantos-validator-node-worker.sh

.PHONY: wheel
wheel: dist/pantos_validator_node-$(PANTOS_VERSION)-py3-none-any.whl

dist/pantos_validator_node-$(PANTOS_VERSION)-py3-none-any.whl: pantos alembic.ini validator-node-config.yml validator-node-config.env
	cp validator-node-config.yml pantos/validator-node-config.yml
	cp validator-node-config.env pantos/validator-node-config.env
	cp alembic.ini pantos/alembic.ini
	poetry build -f wheel
	rm pantos/alembic.ini
	rm pantos/validator-node-config.yml
	rm pantos/validator-node-config.env

.PHONY: debian
debian: dist/pantos-validator-node-$(PANTOS_VERSION)-$(PANTOS_REVISION)_all.deb

dist/pantos-validator-node-$(PANTOS_VERSION)-$(PANTOS_REVISION)_all.deb: linux/ dist/pantos_validator_node-$(PANTOS_VERSION)-py3-none-any.whl
	$(eval debian_package := pantos-validator-node-$(PANTOS_VERSION)-$(PANTOS_REVISION)_all)
	$(eval build_directory := build/debian/$(debian_package))
	mkdir -p $(build_directory)/opt/pantos/validator-node
	cp dist/pantos_validator_node-$(PANTOS_VERSION)-py3-none-any.whl $(build_directory)/opt/pantos/validator-node/
	cp linux/start-web-server $(build_directory)/opt/pantos/validator-node/
	mkdir -p $(build_directory)/etc/systemd/system
	cp linux/pantos-validator-node-server.service $(build_directory)/etc/systemd/system/
	cp linux/pantos-validator-node-celery.service $(build_directory)/etc/systemd/system/
	mkdir -p $(build_directory)/DEBIAN
	cat linux/debian/control | sed -e 's/VERSION/$(PANTOS_VERSION)/g' > $(build_directory)/DEBIAN/control
	cat linux/debian/postinst | sed -e 's/VERSION/$(PANTOS_VERSION)/g' > $(build_directory)/DEBIAN/postinst
	cp linux/debian/prerm $(build_directory)/DEBIAN/prerm
	cp linux/debian/postrm $(build_directory)/DEBIAN/postrm
	chmod 755 $(build_directory)/DEBIAN/postinst
	chmod 755 $(build_directory)/DEBIAN/prerm
	chmod 755 $(build_directory)/DEBIAN/postrm
	cd build/debian/; \
		dpkg-deb --build --root-owner-group -Zgzip $(debian_package)
	mv build/debian/$(debian_package).deb dist/

.PHONY: remote-install
remote-install: dist/pantos-validator-node-$(PANTOS_VERSION)-$(PANTOS_REVISION)_all.deb
	$(eval deb_file := pantos-validator-node-$(PANTOS_VERSION)-$(PANTOS_REVISION)_all.deb)
	scp dist/$(deb_file) $(PANTOS_VALIDATOR_NODE_SSH_HOST):
	ssh -t $(PANTOS_VALIDATOR_NODE_SSH_HOST) "\
		sudo systemctl stop pantos-validator-node-celery;\
		sudo systemctl stop pantos-validator-node-server;\
		sudo apt install -y ./$(deb_file);\
		sudo systemctl start pantos-validator-node-server;\
		sudo systemctl start pantos-validator-node-celery;\
		rm $(deb_file)"

.PHONY: install
install: dist/pantos_validator_node-$(PANTOS_VERSION)-py3-none-any.whl
	poetry run python3 -m pip install dist/pantos_validator_node-$(PANTOS_VERSION)-py3-none-any.whl

.PHONY: uninstall
uninstall:
	poetry run python3 -m pip uninstall -y pantos-validator-node

.PHONY: clean
clean:
	rm -r -f build/
	rm -r -f dist/
	rm -r -f pantos_validator_node.egg-info/
