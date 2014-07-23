#!/usr/bin/env bash

###################################################################
#
#   Extract i18n strings and push them to Transifex.
#
#   You will need to configure your Transifex credentials as
#   described here:
#
#       http://docs.transifex.com/developer/client/setup
#
#   You also need to install gettext:
#
#       https://www.gnu.org/software/gettext/
#
#   Usage:
#
#       ./i18n-push.sh
#
##################################################################

cd `dirname $BASH_SOURCE` && cd ..

echo "Extracting i18n strings..."
python manage.py makemessages --all
python manage.py makemessages --all -d djangojs

echo "Generating dummy strings..."
i18n_tool dummy

read -p "Push strings to transifex? [y/n]  " RESP
if [ "$RESP" = "y" ]; then
    i18n_tool transifex push
    echo " == Pushed strings to Transifex"
else
    echo "Cancelled"
fi
