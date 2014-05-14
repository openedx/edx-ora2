#!/usr/bin/env bash

##################################################
#
#   celery-worker.sh
#
#   Start a worker instance for local development.
#
#   Usage:
#
#       ./celery-worker.sh
#
###################################################

cd `dirname $BASH_SOURCE` && cd ..

# Check whether RabbitMQ is installed
if [ -z `which rabbitmqctl` ]; then
    echo "Please install RabbitMQ: http://www.rabbitmq.com/download.html"
    exit 1;
fi

# Install Python and JS dependencies
./scripts/install.sh

# Configure Django settings
export DJANGO_SETTINGS_MODULE="settings.dev"

# Update the database
echo "Updating the database..."
python manage.py syncdb --migrate -v 0

# Start the RabbitMQ server (ignore errors if it's already started)
echo "Starting RabbitMQ server..."
rabbitmq-server -detached || true

# Start a RabbitMQ node
echo "Starting RabbitMQ node..."
rabbitmqctl start_app

# Start the worker
echo "Starting worker..."
python manage.py celery worker
