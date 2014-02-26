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

# Log configuration, capture everything
import loggers
import logging
logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
        }
    },
    'handlers': {
        'request_token': {
            'level': 'INFO',
            'class': 'loggers.request_id_logger.RequestIDLogHandler',
            'formatter': 'standard',
        }    
    },
    'loggers': {
        '': {
            'handlers': ['request_token'],
            'level': 'INFO',
            'propagate': True,
        }
    }
})
