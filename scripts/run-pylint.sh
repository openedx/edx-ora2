#!/usr/bin/env bash

MAX_PYLINT_VIOLATIONS=438

mkdir -p test/logs
PYLINT_VIOLATIONS=test/logs/pylint.txt
touch $PYLINT_VIOLATIONS

pylint --rcfile=pylintrc openassessment test --msg-template='"{path}:{line}: [{msg_id}({symbol}), {obj}] {msg}"'> $PYLINT_VIOLATIONS
./scripts/run-pylint.py $PYLINT_VIOLATIONS $MAX_PYLINT_VIOLATIONS
