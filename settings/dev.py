"""
Dev-specific Django settings.
"""

# Inherit from base settings
from .base import *

MIDDLEWARE_CLASSES += (
    'django_pdb.middleware.PdbMiddleware',  # Needed to enable shell-on-crash behavior
)

INSTALLED_APPS += (
    'django_pdb',            # Allows post-mortem debugging on exceptions
)