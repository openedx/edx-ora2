"""
Test-specific Django settings.
"""

# Inherit from base settings
from .base import *     # pylint:disable=W0614,W0401

TEST_APPS = (
    'openassessment',
    'openassessment.assessment',
    'openassessment.workflow',
    'openassessment.xblock',
)

# Configure nose
NOSE_ARGS = [
    "-a !acceptance",
    ]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test_ora2db',
        'TEST_NAME': 'test_ora2db',
    },
    'read_replica': {
        'ENGINE': 'django.db.backends.sqlite3',
        'TEST_MIRROR': 'default',
    },
}

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# Install test-specific Django apps
INSTALLED_APPS += ('django_nose',)

# Store uploaded files in a test-specific directory
MEDIA_ROOT = os.path.join(BASE_DIR, 'storage/test')
