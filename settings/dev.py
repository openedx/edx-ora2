"""
Dev-specific Django settings.
"""

# Inherit from base settings
from .base import *

INSTALLED_APPS += (
    'django_pdb',            # Allows post-mortem debugging on exceptions
    'debug_panel',
    'debug_toolbar',
)

MIDDLEWARE_CLASSES += (
    'django_pdb.middleware.PdbMiddleware',  # Needed to enable shell-on-crash behavior
    'debug_panel.middleware.DebugPanelMiddleware',
)

INTERNAL_IPS = ('127.0.0.1',)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'debug-panel',
    },

    # this cache backend will be used by django-debug-panel
    'debug-panel': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'debug-panel',
        'OPTIONS': {
            'MAX_ENTRIES': 200
        }
    }
}
