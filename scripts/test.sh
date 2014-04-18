#!/usr/bin/env bash

# Need to exit with an error code to fail the Travis build
set -e

cd `dirname $BASH_SOURCE` && cd ..
./scripts/install.sh test

echo "Running Python tests..."
export DJANGO_SETTINGS_MODULE="settings.test"
python manage.py test $1

echo "Generating HTML fixtures for JavaScript tests..."
./scripts/render_templates.py apps/openassessment/xblock/static/js/fixtures/templates.json

echo "Running JavaScript tests..."
npm test
