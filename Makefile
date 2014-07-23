all: install test

.PHONY: install test

install-system:
	sudo apt-get update -y -qq
	sudo xargs -a apt-packages.txt apt-get install -y -qq --fix-missing


install-node:
	sudo add-apt-repository -y ppa:chris-lea/node.js
	sudo apt-get update -y -qq
	sudo apt-get install -y -qq nodejs


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

minimize-js:
	node_modules/.bin/uglifyjs $(STATIC_JS)/src/oa_shared.js $(STATIC_JS)/src/*.js > "$(STATIC_JS)/openassessment.min.js"


install-test:
	pip install -q -r requirements/test.txt


install: install-system install-node install-wheels install-python install-js install-nltk-data install-test minimize-js

test:
	./scripts/test.sh
