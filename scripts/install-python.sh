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
