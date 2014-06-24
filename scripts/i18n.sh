#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..

if [ -z $1 ]; then LOCALE='--all'; else LOCALE="-l $1"; fi

python manage.py makemessages $LOCALE
python manage.py makemessages $LOCALE -d djangojs
i18n_tool dummy
python manage.py compilemessages
