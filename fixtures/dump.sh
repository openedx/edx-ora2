#!/usr/bin/env bash

FIXTURES=`dirname $BASH_SOURCE`
EDX_PLATFORM='/edx/app/edxapp/edx-platform'

$EDX_PLATFORM/manage.py lms dumpdata --settings=devstack submissions --indent 4 > $FIXTURES/submission.json
$EDX_PLATFORM/manage.py lms dumpdata --settings=devstack assessment --indent 4 > $FIXTURES/assessments.json
$EDX_PLATFORM/manage.py lms dumpdata --settings=devstack workflow --indent 4 > $FIXTURES/workflow.json
$EDX_PLATFORM/manage.py lms dumpdata --settings=devstack courseware --indent 4 > $FIXTURES/courseware.json
