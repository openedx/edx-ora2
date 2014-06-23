"""
Dev-specific Django settings.
"""
# Inherit from base settings
from .base import *  # pylint:disable=W0614,W0401

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

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'apps_info': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/dev/apps_info.log',
            'formatter': 'simple',
        },
        'apps_debug': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'logs/dev/apps_debug.log',
            'formatter': 'simple',
        },
        'trace': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/dev/trace.log',
            'formatter': 'simple',
            'maxBytes': 1000000,
            'backupCount': 2,
        },
        'events': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/dev/events.log',
            'formatter': 'simple',
        },
        'errors': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'logs/dev/errors.log',
            'formatter': 'simple',
        }
    },
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(name)s [%(levelname)s] %(message)s'
        }
    },
    'loggers': {
        '': {
            'handlers': ['trace', 'errors'],
            'propagate': True,
        },
        'openassessment': {
            'handlers': ['apps_debug', 'apps_info'],
            'propagate': True,
        },
        'submissions': {
            'handlers': ['apps_debug', 'apps_info'],
            'propagate': True,
        },
        'workbench.runtime': {
            'handlers': ['apps_debug', 'apps_info', 'events'],
            'propogate': True,
        }
    },
}


# Store uploaded files in a dev-specific directory
MEDIA_ROOT = os.path.join(BASE_DIR, 'storage/dev')

# Celery Broker
CELERY_BROKER_TRANSPORT = "amqp"
CELERY_BROKER_HOSTNAME = "localhost:5672//"
CELERY_BROKER_USER = "guest"
CELERY_BROKER_PASSWORD = "guest"

BROKER_URL = "{0}://{1}:{2}@{3}".format(
    CELERY_BROKER_TRANSPORT,
    CELERY_BROKER_USER,
    CELERY_BROKER_PASSWORD,
    CELERY_BROKER_HOSTNAME,
)
