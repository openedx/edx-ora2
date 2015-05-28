#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..

echo "Installing Python requirements..."
pip install -q -r requirements/base.txt --exists-action w

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
