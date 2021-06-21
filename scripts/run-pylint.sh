#!/usr/bin/env bash

MAX_PYLINT_VIOLATIONS=0

mkdir -p test/logs
PYLINT_VIOLATIONS=test/logs/pylint.txt
touch $PYLINT_VIOLATIONS

export DJANGO_SETTINGS_MODULE=settings.test
pylint --rcfile=pylintrc openassessment test --msg-template='"{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}"'> $PYLINT_VIOLATIONS
if [ $? -eq 1 ]
then
	echo "Pylint fatal error"
	exit 1
fi
./scripts/run-pylint.py $PYLINT_VIOLATIONS $MAX_PYLINT_VIOLATIONS
