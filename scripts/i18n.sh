#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..

python manage.py makemessages --all
python manage.py makemessages --all -d djangojs
i18n_tool dummy
python manage.py compilemessages
