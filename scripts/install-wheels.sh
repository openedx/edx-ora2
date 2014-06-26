#!/usr/bin/env bash

# Install "wheel" archives of the requirements for running the test suite.
# http://pip.readthedocs.org/en/latest/reference/pip_wheel.html
# This runs in Travis to install pre-built binary packages, which
# means the builds are faster and more reliable.

cd `dirname $BASH_SOURCE` && cd ..

pip install --upgrade pip
pip install wheel

WHEELHOUSE="scripts/data/wheelhouse"

# Ensure that numpy is installed first; otherwise scipy won't be able to install
pip install --use-wheel --no-index --upgrade --find-links=$WHEELHOUSE numpy

# Then install everything else
pip install --use-wheel --no-index --upgrade --find-links=$WHEELHOUSE -r requirements/wheels.txt
