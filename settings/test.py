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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '',
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


# We run Celery in "always eager" mode in the test suite,
# which executes tasks synchronously instead of using the task queue.
CELERY_ALWAYS_EAGER = True
