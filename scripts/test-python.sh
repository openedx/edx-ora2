#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..
./scripts/install-python.sh test

echo "Running Python tests..."
export DJANGO_SETTINGS_MODULE="settings.test"
python manage.py test $1
