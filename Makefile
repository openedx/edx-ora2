.PHONY: help install-python install-js install-test install \
		update-npm-requirements static \
		extract_translations compile_translations generate_dummy_translations validate_translations \
		detect_changed_source_translations pull_translations push_translations check_translations_up_to_date \
		quality test-python render-templates test-js test-js-debug test test-acceptance test-a11y test-sandbox \
		install-osx-requirements

.DEFAULT_GOAL := help

help: ## display this help message
	@echo "Please use \`make <target>' where <target> is one of"
	@perl -nle'print $& if m{^[a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

clean: ## remove generated byte code, coverage reports, and build artifacts
	find openassessment/ -name '__pycache__' -exec rm -rf {} +
	find openassessment/ -name '*.pyc' -exec rm -f {} +
	find openassessment/ -name '*.pyo' -exec rm -f {} +
	find openassessment/ -name '*~' -exec rm -f {} +
	coverage erase
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

##################
# Install commands
##################

install-python: ## Install python dependencies
	pip install -r requirements/base.txt --only-binary=lxml

install-js: ## install JavaScript dependencies
	npm install

install-test: ## install requirements for tests
	pip install -r requirements/test.txt
	python setup.py develop --quiet  # XBlock plugin (openassessment) has to be installed via entry_points.

install: install-python install-js install-test static ## install all dependencies

COMMON_CONSTRAINTS_TXT=requirements/common_constraints.txt
.PHONY: $(COMMON_CONSTRAINTS_TXT)
$(COMMON_CONSTRAINTS_TXT):
	wget -O "$(@)" https://raw.githubusercontent.com/edx/edx-lint/master/edx_lint/files/common_constraints.txt || touch "$(@)"
	echo "$(COMMON_CONSTRAINTS_TEMP_COMMENT)" | cat - $(@) > temp && mv temp $(@)

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: $(COMMON_CONSTRAINTS_TXT)  ## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
    # global common_constraints has this pin.
	sed 's/django-simple-history==3.0.0//g' requirements/common_constraints.txt > requirements/common_constraints.tmp
	mv requirements/common_constraints.tmp requirements/common_constraints.txt
	pip install -qr requirements/pip-tools.txt
	pip-compile --upgrade --allow-unsafe -o requirements/pip.txt requirements/pip.in
	pip-compile --upgrade -o requirements/pip-tools.txt requirements/pip-tools.in
	pip install -qr requirements/pip.txt
	pip install -qr requirements/pip-tools.txt
	pip-compile --upgrade -o requirements/base.txt requirements/base.in
	pip-compile --upgrade -o requirements/test.txt requirements/test.in
	pip-compile --upgrade -o requirements/quality.txt requirements/quality.in
	pip-compile --upgrade -o requirements/test-acceptance.txt requirements/test-acceptance.in
	pip-compile --upgrade -o requirements/tox.txt requirements/tox.in
	pip-compile --upgrade -o requirements/ci.txt requirements/ci.in
	pip-compile --upgrade -o requirements/docs.txt requirements/docs.in
	# Delete django pin from test requirements to avoid tox version collision
	sed -i.tmp '/^[d|D]jango==/d' requirements/test.txt
	sed -i.tmp '/^djangorestframework==/d' requirements/test.txt
	# Delete extra metadata that causes build to fail
	sed -i.tmp '/^--index-url/d' requirements/*.txt
	sed -i.tmp '/^--extra-index-url/d' requirements/*.txt
	sed -i.tmp '/^--trusted-host/d' requirements/*.txt
	# Delete temporary files
	rm requirements/*.txt.tmp

##############################
# Generate js/css output files
##############################

STATIC_JS = openassessment/xblock/static/js
STATIC_CSS = openassessment/xblock/static/css

update-npm-requirements: ## update NPM requrements
	npm update --silent
	cp ./node_modules/backgrid/lib/backgrid*.js $(STATIC_JS)/lib/backgrid/
	cp ./node_modules/backgrid/lib/backgrid*.css $(STATIC_CSS)/lib/backgrid/

static: ## Webpack JavaScript and SASS source files
	npm run build

################
#Translations Handling
################

extract_translations: ## creates the django-partial.po & django-partial.mo files
	cd ./openassessment && django-admin makemessages -l en -v1 -d django
	cd ./openassessment && django-admin makemessages -l en -v1 -d djangojs

compile_translations: ## compiles the *.po & *.mo files
	cd ./openassessment/ && i18n_tool generate -v && cd ..

generate_dummy_translations: ## generate dummy translations
	i18n_tool dummy

validate_translations: ## Test translation files
	cd ./openassessment/ && i18n_tool validate -v

detect_changed_source_translations: ## check if translation files are up-to-date
	i18n_tool changed

pull_translations: ## pull translations from Transifex
	tx pull -a -f -t --mode reviewed --minimum-perc=1

push_translations: ## push source translation files (.po) to Transifex
	tx push -s

check_translations_up_to_date: extract_translations compile_translations generate_dummy_translations detect_changed_source_translations ## extract, compile, and check if translation files are up-to-date

update_translations: extract_translations compile_translations generate_dummy_translations pull_translations ## extract, compile, and pull translations from Transifex

################
#Tests and checks
################

quality: ## Run linting and code quality checks
	npm run lint
	./scripts/run-pycodestyle.sh
	./scripts/run-pylint.sh

test-python: ## Run Python tests
	pytest

render-templates: ## Render HTML templates
	./scripts/render-templates.sh

test-js: render-templates ## Run JavaScript frontend tests
	./scripts/test-js.sh

test-js-debug: render-templates ## Debug JavaScript tests using Karma
	./scripts/js-debugger.sh

test: quality test-python test-js ## Run quality checks and tests for Python and JavaScript

test-acceptance: ## acceptance and a11y tests require a functioning sandbox, and do not run on travis
	./scripts/test-acceptance.sh tests

test-a11y: ## Run accessibility tests
	./scripts/test-acceptance.sh accessibility

test-sandbox: test-acceptance test-a11y ## Run acceptance and accessibility tests

install-osx-requirements: ## Install OSX specific requirements using Homebrew
	brew install gettext
	brew link gettext --force

##################
#Devstack commands
##################

install-local-ora: ## installs your local ORA2 code into the LMS and Studio python virtualenvs
	docker exec -t edx.devstack.lms bash -c '. /edx/app/edxapp/venvs/edxapp/bin/activate && cd /edx/app/edxapp/edx-platform && pip uninstall -y ora2 && pip install -e /edx/src/edx-ora2 && pip freeze | grep ora2'
	docker exec -t edx.devstack.cms bash -c '. /edx/app/edxapp/venvs/edxapp/bin/activate && cd /edx/app/edxapp/edx-platform && pip uninstall -y ora2 && pip install -e /edx/src/edx-ora2 && pip freeze | grep ora2'

install_transifex_client: ## Install the Transifex client
	# Instaling client will skip CHANGELOG and LICENSE files from git changes
	# so remind the user to commit the change first before installing client.
	git diff -s --exit-code HEAD || { echo "Please commit changes first."; exit 1; }
	curl -o- https://raw.githubusercontent.com/transifex/cli/master/install.sh | bash
	# Load the PATH changes to make transifex client accessible from any directory i.e. openassessment for pull translations
	export PATH="$(PATH):$(pwd)"
	git checkout -- LICENSE ## overwritten by Transifex installer
	rm README.md ## pulled by Transifex installer
