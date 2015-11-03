#!/usr/bin/env bash

############################################################
#
#   test-acceptance.sh
#
#   Runs acceptance tests from a specified file against
#   an edX platform sandbox.
#
#   Note: this script is invoked from the ORA Makefile and
#   should not normally be used directly.
#
#   Usage:
#
#       ./test-acceptance.sh {test_file}
#
############################################################

cd `dirname $BASH_SOURCE` && cd ..

# Note: support BASE_URL as a synonym for ORA_SANDBOX_URL for backward compatibility
if [[ $BASE_URL ]]; then
    export ORA_SANDBOX_URL="$BASE_URL"
fi

if [[ -z $ORA_SANDBOX_URL ]]; then
    echo "Error: ORA_SANDBOX_URL must be set to point to your sandbox"
    exit 1
fi

mkdir -p test/logs
cd test/logs
export SELENIUM_BROWSER=phantomjs

test_name="${1:-acceptance}"

echo "Running acceptance tests from ${test_name}.py against the sandbox..."

python ../acceptance/${test_name}.py
