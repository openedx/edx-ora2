#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..

# Cleanup uploaded files from previous test runs (AI classifiers)
git clean -xfd "./storage/test/"

./scripts/install-python.sh test

echo "Running Python tests..."
export DJANGO_SETTINGS_MODULE="settings.test"
python manage.py test $1
