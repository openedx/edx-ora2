#!/usr/bin/env bash

###################################################
#
#   install-sandbox-course.sh
#
#   Install a test course in a sandbox.
#   Meant to be run from within the sandbox.
#
#   Usage:
#
#       ./install-sandbox-course.sh
#
###################################################


cd `dirname $BASH_SOURCE` && cd ..

EDX_PLATFORM='/edx/app/edxapp/edx-platform'
COURSE_TARBALL="scripts/data/test-course.tar.gz"
COURSE_ORG="edX"
COURSE_NUM="ORA203"
COURSE_RUN="course"
COURSE_DATA="/edx/var/edxapp/data/$COURSE_NUM"
mkdir -p $COURSE_DATA
COURSE_ID="$COURSE_ORG/$COURSE_NUM/$COURSE_RUN"

echo "Removing old test course..."
rm -rf $COURSE_DATA/$COURSE_RUN
rm -rf $COURSE_DATA/$COURSE_NUM
echo "Done"

echo "Decompressing test course"
tar -C $COURSE_DATA -zxvf "$COURSE_TARBALL"
echo "Done"

echo "Importing test course..."
SERVICE_VARIANT=cms python $EDX_PLATFORM/manage.py cms \
    import $COURSE_DATA $COURSE_RUN --settings aws
echo "Done"
