#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..

STATIC_JS="openassessment/xblock/static/js"

echo "Installing Node requirements..."
if [ -z `which npm` ]; then
    echo "Please install NodeJS: http://nodejs.org/"
    exit 1
fi

npm config set loglevel warn
npm install

echo "Minimizing XBlock JavaScript..."
echo "(set DEBUG_JS=1 to preserve indentation and line breaks)"
if [[ -n "$DEBUG_JS" ]]; then
    UGLIFY_EXTRA_ARGS="--beautify"
fi

node_modules/.bin/uglifyjs $STATIC_JS/src/oa_shared.js $STATIC_JS/src/lms/*.js $UGLIFY_EXTRA_ARGS > "$STATIC_JS/openassessment-lms.min.js"
node_modules/.bin/uglifyjs $STATIC_JS/src/oa_shared.js $STATIC_JS/src/studio/*.js $UGLIFY_EXTRA_ARGS > "$STATIC_JS/openassessment-studio.min.js"
