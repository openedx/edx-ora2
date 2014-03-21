#!/usr/bin/env bash

# Need to exit with an error code to fail the Travis build
set -e

cd `dirname $BASH_SOURCE` && cd ..
./scripts/install.sh test

echo "Running Python tests..."
export DJANGO_SETTINGS_MODULE="settings.test"
python manage.py test

echo "Running JavaScript tests..."
npm test

echo "Testing fixture import..."
# This uses the test database, because we're using test settings
rm -rf testdb
python manage.py syncdb --migrate --noinput -v 0

# There's an issue in Django 1.4 about loaddata not exiting with status 1 on error:
# https://code.djangoproject.com/ticket/20538
# Instead, we check if we can successfully match error text in the command output
if python manage.py loaddata \
    fixtures/submission.json fixtures/assessments.json fixtures/workflow.json 2>&1 \
    | tee fixture_err.log \
    | grep -q "[Pp]roblem"; then
    echo "Problem occurred when loading fixture file:"
    cat fixture_err.log
    exit 1
else
    echo "Success!"
fi
