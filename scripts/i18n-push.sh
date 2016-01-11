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

# Note we only extract the English language strings so they can be
# sent to Transifex. All other language strings will be pulled
# down from Transifex and so don't need to be generated.

echo "Extracting i18n strings..."
django-admin.py makemessages --locale=en --ignore="edx-ora2/*" --ignore="build/*" --ignore="node_modules/*"

echo "Extracting client-side i18n strings..."
django-admin.py makemessages --locale=en --ignore="edx-ora2/*" --ignore="build/*" --ignore="node_modules/*" -d djangojs

echo "Generating dummy strings..."
i18n_tool dummy
i18n_tool generate
