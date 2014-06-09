#!/usr/bin/env bash

set -e

cd `dirname $BASH_SOURCE` && cd ..
STATIC_JS="openassessment/xblock/static/js"

if [[ -n "$1" ]]; then
    REQS="$1"
else
    REQS="dev"
fi

echo "Installing Python requirements..."
pip install -q -r requirements/$REQS.txt

echo "Installing the OpenAssessment XBlock..."
cat <<EOF | python -
import pkg_resources
import sys
try:
    pkg_resources.require('ora2')
except pkg_resources.DistributionNotFound:
    sys.exit(1)
EOF
ORA2_MISSING=$?
if [[ $ORA2_MISSING -eq 1 ]]; then
    pip install -q -e .
    echo "Installed."
else
    echo "Already installed."
fi
