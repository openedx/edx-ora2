##################
# Install commands
##################
install-python:
	pip install -r requirements/django.txt
	pip install -r requirements/base.txt --only-binary=lxml,libsass

install-js:
	npm install

install-test:
	pip install -r requirements/test.txt

install: install-python install-js install-test javascript sass

##############################
# Generate js/css output files
##############################
STATIC_JS = openassessment/xblock/static/js
STATIC_CSS = openassessment/xblock/static/css

update-npm-requirements:
	npm update --silent
	cp ./node_modules/backgrid/lib/backgrid*.js $(STATIC_JS)/lib/backgrid/
	cp ./node_modules/backgrid/lib/backgrid*.css $(STATIC_CSS)/lib/backgrid/

javascript: update-npm-requirements
	node_modules/.bin/uglifyjs $(STATIC_JS)/src/oa_shared.js $(STATIC_JS)/src/*.js $(STATIC_JS)/src/lms/*.js $(STATIC_JS)/lib/backgrid/backgrid.min.js -c warnings=false > "$(STATIC_JS)/openassessment-lms.min.js"
	node_modules/.bin/uglifyjs $(STATIC_JS)/src/oa_shared.js $(STATIC_JS)/src/*.js $(STATIC_JS)/src/studio/*.js $(STATIC_JS)/lib/backgrid/backgrid.min.js -c warnings=false > "$(STATIC_JS)/openassessment-studio.min.js"

sass:
	python scripts/compile_sass.py

verify-generated-files:
	@git diff --quiet || (echo 'Modifications exist locally! Run `make javascript` or `make sass` to update bundled files.'; exit 1)

################
#Tests and checks
################
quality:
	./node_modules/.bin/jshint $(STATIC_JS)/src -c .jshintrc --verbose
	./node_modules/jscs/bin/jscs $(STATIC_JS)/src --verbose
	./scripts/run-pep8.sh
	./scripts/run-pylint.sh

test-python:
	coverage run manage.py test openassessment

render-templates:
	./scripts/render-templates.sh

test-js: render-templates
	./scripts/test-js.sh

test-js-debug: render-templates
	./scripts/js-debugger.sh

test: quality test-python test-js

# acceptance and a11y tests require a functioning sandbox, and do not run on travis
test-acceptance:
	./scripts/test-acceptance.sh tests

test-a11y:
	./scripts/test-acceptance.sh accessibility

test-sandbox: test-acceptance test-a11y
