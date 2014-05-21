#!/usr/bin/env bash

# Need to exit with an error code to fail the Travis build
set -e

cd `dirname $BASH_SOURCE` && cd ..
./scripts/test-python.sh $1
./scripts/test-js.sh
