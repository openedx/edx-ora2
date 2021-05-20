#!/usr/bin/env bash


cd `dirname $BASH_SOURCE` && cd ..

# Install dependencies
make install-python
make install-js
make static

# Configure Django settings
export DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-"settings.dev"}

# Create the database
echo "Updating the database..."
python manage.py syncdb --migrate -v 0

echo "Starting server..."
python manage.py runserver_plus "${@:1}"
