all: install test

.PHONY: install test

install-system:
	@echo '***************** install-system started *****************'
	sudo apt-get update -y -qq
	sudo xargs -a apt-packages.txt apt-get install -y -qq --fix-missing
	@echo '***************** install-system finished *****************'

install-node:
	@echo '***************** install-node started *****************'
	sudo add-apt-repository -y ppa:chris-lea/node.js
	sudo apt-get update -y -qq
	sudo apt-get install -y -qq nodejs
	@echo '***************** install-node finished *****************'


install-wheels:
	@echo '***************** install-wheels started *****************'
	./scripts/install-wheels.sh
	@echo '***************** install-wheels finished *****************'

install-python:
	@echo '***************** install-python started *****************'
	./scripts/install-python.sh
	@echo '***************** install-python finished *****************'

install-js:
	@echo '***************** install-js started *****************'
	sudo npm config set loglevel warn
	npm install
	@echo '***************** install-js finished *****************'

install-nltk-data:
	@echo '***************** install-nltk-data started *****************'
	./scripts/download-nltk-data.sh
	@echo '***************** install-nltk-data finished *****************'


STATIC_JS = openassessment/xblock/static/js

javascript:
	node_modules/.bin/uglifyjs $(STATIC_JS)/src/oa_shared.js $(STATIC_JS)/src/*.js $(STATIC_JS)/src/lms/*.js > "$(STATIC_JS)/openassessment-lms.min.js"
	node_modules/.bin/uglifyjs $(STATIC_JS)/src/oa_shared.js $(STATIC_JS)/src/*.js $(STATIC_JS)/src/studio/*.js > "$(STATIC_JS)/openassessment-studio.min.js"


install-test:
	pip install -q -r requirements/test.txt

install-dev:
	sudo gem install sass
	pip install -q -r requirements/dev.txt

install: install-system install-node install-wheels install-python install-js install-nltk-data install-test install-dev javascript

test:
	./scripts/test.sh
