#!/usr/bin/env bash

# Need to exit with an error code to fail the Travis build
set -e

cd `dirname $BASH_SOURCE` && cd ..
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-"settings.test_with_coverage"}
./scripts/test-python.sh $1
./scripts/render-templates.sh
./scripts/test-js.sh
