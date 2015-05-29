all: install test

.PHONY: install test

# not used by travis
install-system:
	sudo apt-get update -qq
	sudo xargs -a apt-packages.txt apt-get install -qq --fix-missing

# not used by travis
install-node:
	sudo add-apt-repository -y ppa:chris-lea/node.js
	sudo apt-get update -qq
	sudo apt-get install -qq nodejs

install-wheels:
	./scripts/install-wheels.sh


install-python:
	./scripts/install-python.sh

install-js:
	npm config set loglevel warn
	npm install

install-nltk-data:
	./scripts/download-nltk-data.sh


STATIC_JS = openassessment/xblock/static/js

javascript:
	node_modules/.bin/uglifyjs $(STATIC_JS)/src/oa_shared.js $(STATIC_JS)/src/*.js $(STATIC_JS)/src/lms/*.js > "$(STATIC_JS)/openassessment-lms.min.js"
	node_modules/.bin/uglifyjs $(STATIC_JS)/src/oa_shared.js $(STATIC_JS)/src/*.js $(STATIC_JS)/src/studio/*.js > "$(STATIC_JS)/openassessment-studio.min.js"


install-test:
	pip install -q -r requirements/test.txt

install-sys-requirements: install-system install-node

install-dev:
	gem install sass
	pip install -q -r requirements/dev.txt

install: install-wheels install-python install-js install-nltk-data install-test install-dev javascript

test:
	./scripts/test.sh
