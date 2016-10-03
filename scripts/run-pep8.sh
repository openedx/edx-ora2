#!/usr/bin/env bash

MAX_PEP8_VIOLATIONS=111

mkdir -p test/logs
PEP8_VIOLATIONS=test/logs/pep8.txt
touch $PEP8_VIOLATIONS

pep8 --config=.pep8 openassessment test > $PEP8_VIOLATIONS
NUM_PEP8_VIOLATIONS=$(cat $PEP8_VIOLATIONS | wc -l)

echo "Found" $NUM_PEP8_VIOLATIONS "pep8 violations, threshold is" $MAX_PEP8_VIOLATIONS
if [[ $NUM_PEP8_VIOLATIONS -gt $MAX_PEP8_VIOLATIONS ]]; then
    cat $PEP8_VIOLATIONS
    echo "NUMBER OF PEP8 VIOLATIONS ("$NUM_PEP8_VIOLATIONS") EXCEEDED THRESHOLD" $MAX_PEP8_VIOLATIONS
    exit 1
fi
