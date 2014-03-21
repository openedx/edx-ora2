#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..
STATIC_JS="apps/openassessment/xblock/static/js"

if [[ -n "$1" ]]; then
    REQS="$1"
else
    REQS="dev"
fi

echo "Installing Python requirements..."
pip install -q -r requirements/$REQS.txt

echo "Installing XBlock..."
pip install -q -e .

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

node_modules/.bin/uglifyjs $STATIC_JS/src/*.js $UGLIFY_EXTRA_ARGS > "$STATIC_JS/openassessment.min.js"
