#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..

# Install "wheel" archives of the requirements for running the test suite.
# http://pip.readthedocs.org/en/latest/reference/pip_wheel.html
# This runs in Travis to install pre-built binary packages, which
# means the builds are faster and more reliable.
pip install --upgrade pip
pip install wheel

WHEELHOUSE="scripts/data/wheelhouse"

echo "********************* INSTALLING NUMPY WHEEL *********************"
# Ensure that numpy is installed first; otherwise scipy won't be able to install
pip install --use-wheel --no-index --upgrade --find-links=$WHEELHOUSE numpy
echo "********************* NUMPY WHEEL INSTALLED *********************"

echo "********************* INSTALLING OTHER WHEELS *********************"
# Then install everything else
pip install --use-wheel --no-index --upgrade --find-links=$WHEELHOUSE -r requirements/wheels.txt
echo "********************* OTHER WHEELS INSTALLED *********************"