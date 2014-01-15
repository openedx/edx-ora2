"""
Test-specific Django settings.
"""

# Inherit from base settings
from .base import *

TEST_APPS = ('common_grading', 'peer_grading')

# Configure nose
NOSE_ARGS = [
    '--with-coverage',
    '--cover-package=' + ",".join(TEST_APPS)
]

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# Configure lettuce
LETTUCE_APPS = TEST_APPS
LETTUCE_SERVER_PORT = 8005

# Install test-specific Django apps
INSTALLED_APPS += ('django_nose', 'lettuce.django')
