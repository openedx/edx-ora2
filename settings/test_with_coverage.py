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


import warnings

from django.core.cache import CacheKeyWarning

warnings.simplefilter("ignore", CacheKeyWarning)
