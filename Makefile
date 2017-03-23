all: install test

.PHONY: install test

# not used by travis
install-system:
	sudo apt-get update -qq
	sudo xargs -a apt-packages.txt apt-get install -qq --fix-missing

# not used by travis
install-node:
	sudo apt-get install -qq nodejs

install-wheels:
	./scripts/install-wheels.sh


install-python:
	./scripts/install-python.sh

install-js:
	npm install

install-nltk-data:
	./scripts/download-nltk-data.sh


STATIC_JS = openassessment/xblock/static/js
STATIC_CSS = openassessment/xblock/static/css

javascript: update-npm-requirements
	node_modules/.bin/uglifyjs $(STATIC_JS)/src/oa_shared.js $(STATIC_JS)/src/*.js $(STATIC_JS)/src/lms/*.js $(STATIC_JS)/lib/backgrid/backgrid.min.js -c warnings=false > "$(STATIC_JS)/openassessment-lms.min.js"
	node_modules/.bin/uglifyjs $(STATIC_JS)/src/oa_shared.js $(STATIC_JS)/src/*.js $(STATIC_JS)/src/studio/*.js $(STATIC_JS)/lib/backgrid/backgrid.min.js -c warnings=false > "$(STATIC_JS)/openassessment-studio.min.js"

sass:
	python scripts/compile_sass.py

verify-generated-files:
	@git diff --quiet || (echo 'Modifications exist locally! Run `make javascript` or `make sass` to update bundled files.'; exit 1)

install-test:
	pip install -q -r requirements/test.txt

install-sys-requirements: install-system install-node
	npm config set loglevel warn

install-dev:
	pip install -q -r requirements/dev.txt

install: install-wheels install-python install-js install-nltk-data install-test install-dev javascript sass

quality:
	./node_modules/.bin/jshint $(STATIC_JS)/src -c .jshintrc --verbose
	./node_modules/jscs/bin/jscs $(STATIC_JS)/src --verbose
	./scripts/run-pep8.sh
	./scripts/run-pylint.sh

test: quality test-python test-js

test-python:
	./scripts/test-python.sh

render-templates:
	./scripts/render-templates.sh

test-js: render-templates
	./scripts/test-js.sh

test-js-debug: render-templates
	./scripts/js-debugger.sh

test-sandbox: test-acceptance test-a11y

test-acceptance:
	./scripts/test-acceptance.sh tests

test-a11y:
	./scripts/test-acceptance.sh accessibility

update-npm-requirements:
	npm update --silent
	cp ./node_modules/backgrid/lib/backgrid*.js $(STATIC_JS)/lib/backgrid/
	cp ./node_modules/backgrid/lib/backgrid*.css $(STATIC_CSS)/lib/backgrid/
