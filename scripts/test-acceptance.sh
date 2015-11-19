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

test_name="${1:-acceptance}"


# The machines that these tests run on in jenkins have an old
# version of npm which doesn't seem to work with the
# requirements in this repo. There is a devops ticket for
# this, but it may be better to wait until some of the other
# work they have going on now is done before attempting to
# install the custom rules via npm. This bit of code is a
# work around for that. It will work both in jenkins and for
# local runs of the tests.
if [[ "${test_name}" = "accessibility" ]]; then
    export BOKCHOY_A11Y_CUSTOM_RULES_FILE=../../test/custom_a11y_rules.js

    if [[ ! -f $BOKCHOY_A11Y_CUSTOM_RULES_FILE ]]; then
        echo "Custom a11y rules file not found. Fetching it..."
        custom_a11y_version=8633ea2fd04d84d69c4610bbfbf38db32ad005a9
        curl https://raw.githubusercontent.com/edx/edx-custom-a11y-rules/${custom_a11y_version}/lib/custom_a11y_rules.js > ${BOKCHOY_A11Y_CUSTOM_RULES_FILE}
    fi
fi

echo "Running acceptance tests from ${test_name}.py against the sandbox..."
python ../acceptance/${test_name}.py
