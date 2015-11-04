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
    '--with-coverage',
    '--cover-package=' + ",".join(TEST_APPS),
    '--cover-branches',
    '--cover-erase',
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

SECRET_KEY = ')68&amp;-c!+og)cy$o9pju_$c707+fett&amp;ph%t%gqgu-@5)!cl$cr'

# Silence cache key warnings
# https://docs.djangoproject.com/en/1.4/topics/cache/#cache-key-warnings
import warnings
from django.core.cache import CacheKeyWarning
warnings.simplefilter("ignore", CacheKeyWarning)
