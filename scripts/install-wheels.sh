#!/usr/bin/env bash

cd `dirname $BASH_SOURCE` && cd ..

# Install "wheel" archives of the requirements for running the test suite.
# http://pip.readthedocs.org/en/latest/reference/pip_wheel.html
# This runs in Travis to install pre-built binary packages, which
# means the builds are faster and more reliable.
pip install --upgrade pip
pip install wheel

# Ensure that numpy is installed first; otherwise scipy won't be able to install
pip install --use-wheel numpy==1.6.2

# Then install everything else
pip install --use-wheel -r requirements/wheels.txt
