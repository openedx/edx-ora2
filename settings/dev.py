"""
Dev-specific Django settings.
"""

# Inherit from base settings
from .base import *

INSTALLED_APPS += (
    'django_pdb',            # Allows post-mortem debugging on exceptions
    'debug_toolbar',
)

MIDDLEWARE_CLASSES += (
    'django_pdb.middleware.PdbMiddleware',  # Needed to enable shell-on-crash behavior
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

INTERNAL_IPS = ('127.0.0.1',)

LOGGING['loggers']['django.request']['level'] = 'DEBUG'
