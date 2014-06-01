"""
Settings for running workbench in Vagrant.
To mimic production, the Vagrant setup uses:

    * gunicorn (run multiple server processes)
    * memcached
    * mysql
    * rabbitmq

"""

# Inherit from base settings
from .base import *  # pylint:disable=W0614,W0401

VAGRANT_HOME = "/home/vagrant"
REPO_ROOT = u"{home}/edx-ora2".format(home=VAGRANT_HOME)

DEBUG = False

INSTALLED_APPS += ('gunicorn',)

STATIC_ROOT = u"{home}/static".format(home=VAGRANT_HOME)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'workbench',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': 60 * 60 * 8
    }
}

LOG_ROOT = u"{repo}/logs/vagrant".format(repo=REPO_ROOT)
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
            'filename': u'{}/apps_info.log'.format(LOG_ROOT),
            'formatter': 'simple',
        },
        'apps_debug': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': u'{}/apps_debug.log'.format(LOG_ROOT),
            'formatter': 'simple',
        },
        'trace': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': u'{}/trace.log'.format(LOG_ROOT),
            'formatter': 'simple',
            'maxBytes': 1000000,
            'backupCount': 2,
        },
        'events': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': u'{}/events.log'.format(LOG_ROOT),
            'formatter': 'simple',
        },
        'errors': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': u'{}/errors.log'.format(LOG_ROOT),
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

# AI algorithm configuration
ORA2_AI_ALGORITHMS = {
    'fake': 'openassessment.assessment.worker.algorithm.FakeAIAlgorithm',
    'ease': 'openassessment.assessment.worker.algorithm.EaseAIAlgorithm'
}

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
