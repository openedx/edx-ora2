#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..

echo "Starting JavaScript tests in a browser..."
./node_modules/karma/bin/karma start --single-run=false --browsers Chrome --reporters=html --autoWatch
