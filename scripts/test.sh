#!/usr/bin/env bash

# Need to exit with an error code to fail the Travis build
set -e

cd `dirname $BASH_SOURCE` && cd ..
./scripts/test-python.sh
./scripts/test-js.sh
./scripts/build-docs.sh
