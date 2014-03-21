"""
Dev-specific Django settings.
"""
# Inherit from base settings
from .base import *

INSTALLED_APPS += (
    'django_pdb',            # Allows post-mortem debugging on exceptions
    'debug_toolbar',
    'debug_panel',
)

MIDDLEWARE_CLASSES += (
    'django_pdb.middleware.PdbMiddleware',  # Needed to enable shell-on-crash behavior
    'debug_panel.middleware.DebugPanelMiddleware',
)

# We need to use explicit discovery or we'll have problems with syncdb and
# displaying the admin site. See:
# http://django-debug-toolbar.readthedocs.org/en/1.0/installation.html#explicit-setup
DEBUG_TOOLBAR_PATCH_SETTINGS = False

INTERNAL_IPS = ('127.0.0.1',)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 60 * 60 * 8
    }
}
