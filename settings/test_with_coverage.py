"""
Django settings for running tests with coverage.
"""

# Inherit from the test settings
from .test import *     # pylint:disable=W0614,W0401

# Configure nose so that tests are run with coverage
NOSE_ARGS = [
    "-a !acceptance",
    '--with-coverage',
    '--cover-package=' + ",".join(TEST_APPS),
    '--cover-branches',
    '--cover-erase',
    ]

SECRET_KEY = ')68&amp;-c!+og)cy$o9pju_$c707+fett&amp;ph%t%gqgu-@5)!cl$cr'
