#!/usr/bin/env bash

# Need to exit with an error code to fail the Travis build
set -e

pip install -q Sphinx sphinx_rtd_theme

# go into docs directory
cd docs/en_us

# build course authors docs
cd course_authors
if [ -f requirements.txt ]; then
    pip install -q -r requirements.txt
fi
make html
cd ..

# build developer docs
cd developers
if [ -f requirements.txt ]; then
    pip install -q -r requirements.txt
fi
make html
cd ..

# go back where we started
cd ../..
