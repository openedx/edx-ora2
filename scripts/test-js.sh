#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..
./scripts/install-js.sh

echo "Generating HTML fixtures for JavaScript tests..."
export DJANGO_SETTINGS_MODULE="settings.test"
./scripts/render_templates.py openassessment/xblock/static/js/fixtures/templates.json

echo "Running JavaScript tests..."
npm test
