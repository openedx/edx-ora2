#!/usr/bin/env bash


######################################################################################################
#
#   install.sh
#
#   Install course, user, submission, and assessment fixtures for testing Open Assessment
#   within the LMS / Studio.
#
#   Designed to be run within a devstack VM (https://github.com/edx/configuration/wiki/edX-Developer-Stack).
#
#   WARNING: This will wipe out the databases and installed courses!  Use with extreme caution!
#
#   Usage:
#
#       ./install.sh
#
######################################################################################################

set -e

FIXTURES=`dirname $BASH_SOURCE`
EDX_PLATFORM='/edx/app/edxapp/edx-platform'
COURSE_DATA='/edx/var/edxapp/data'
COURSE_ID='edx/101/2014_Spring'
ITEM='i4x://edx/101/openassessment'

function echo_task {
    echo $'\n'
    echo "====== $1"
}


# Scary warning message
read -p "Warning: this will wipe out all state in the LMS and Studio.  Are you sure? [Y/N]   " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi


# Drop and recreate the edxapp database
echo_task "Resetting relational database..."
mysql -u root < $FIXTURES/reset-db.sql
echo "Done"

# Clear the Mongo database
echo_task "Resetting Mongo database..."
mongo --quiet --eval 'db.getMongo().getDBNames().forEach(function(i){db.getSiblingDB(i).dropDatabase()})'
echo "Done"

# Delete any old copies of this course fixture
echo_task "Deleting courses..."
rm -rf $COURSE_DATA/2014_Spring
rm -rf $COURSE_DATA/100
echo "Done"

# Syncdb and migrate
echo_task "Creating database tables and running migrations..."
python $EDX_PLATFORM/manage.py lms syncdb --settings devstack --noinput
python $EDX_PLATFORM/manage.py lms migrate --settings devstack --noinput
echo "Done"

# Untar the course fixture
echo_task "Decompressing course fixture..."
tar -C $COURSE_DATA -zxvf $FIXTURES/2014_Spring.tar.gz
echo "Done"

# Import the course fixture
echo_task "Importing course fixture..."
python $EDX_PLATFORM/manage.py cms import $COURSE_DATA 2014_Spring --settings devstack
echo "Done"

# Create test users
echo_task "Creating test users..."
echo "Note: You may see some errors about connecting to the discussion service -- you can safely ignore these!"
python $EDX_PLATFORM/manage.py cms --settings devstack create_user -e staff@example.com -p edx -s -c $COURSE_ID
python $EDX_PLATFORM/manage.py cms --settings devstack create_user -e proof@example.com -p edx -c $COURSE_ID
python $EDX_PLATFORM/manage.py cms --settings devstack create_user -e submitter@example.com -p edx -c $COURSE_ID
echo "Done"

# Create dummy submissions and assessments
echo_task "Creating dummy submissions and assessments"
$EDX_PLATFORM/manage.py lms loaddata --settings=devstack $FIXTURES/submission.json
$EDX_PLATFORM/manage.py lms loaddata --settings=devstack $FIXTURES/assessments.json
$EDX_PLATFORM/manage.py lms loaddata --settings=devstack $FIXTURES/workflow.json
$EDX_PLATFORM/manage.py lms loaddata --settings=devstack $FIXTURES/courseware.json


echo "Done"
