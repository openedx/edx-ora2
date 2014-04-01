"""
Test-specific Django settings.
"""

# Inherit from base settings
from .base import *

TEST_APPS = (
    'openassessment',
    'openassessment.assessment',
    'openassessment.workflow',
    'openassessment.xblock',
    'submissions',
)

# Configure nose
NOSE_ARGS = [
    '--with-coverage',
    '--cover-package=' + ",".join(TEST_APPS),
    '--cover-branches',
    '--cover-erase',
    ]

# This will still use an in-memory database for the unit tests,
# but will create an on-disk database for testing migrations/fixture installation.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'testdb',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'


# Install test-specific Django apps
INSTALLED_APPS += ('django_nose',)

EDX_ORA2["EVENT_LOGGER"] = "openassessment.workflow.test.events.fake_event_logger"
