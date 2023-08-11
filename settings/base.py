"""
Base settings for ORA2.
"""

import os

DEBUG = True

ADMINS = (
    ('admin', 'admin'),
)

MANAGERS = ADMINS

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'ora2db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = ')68&amp;-c!+og)cy$o9pju_$c707+fett&amp;ph%t%gqgu-@5)!cl$cr'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
            ],
            'debug': DEBUG,
        },
    },
]

MIDDLEWARE = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'urls'

# Python dotted path to the WSGI application used by Django's runserver.
# WSGI_APPLICATION = 'wsgi.application'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',

    # Waffle flag/switches
    'waffle',

    # XBlock
    'workbench',
    'sample_xblocks.basic',  # Needs to be an app for template lookup

    # ora2 apps
    'submissions',
    'openassessment',
    'openassessment.fileupload',
    'openassessment.workflow',
    'openassessment.assessment',
    'openassessment.staffgrader',
)

# TODO: add config for XBLOCK_WORKBENCH { SCENARIO_CLASSES }
WORKBENCH = {
    'reset_state_on_restart': False,
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'default_loc_mem',
    },
}

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

LOCALE_PATHS = [os.path.join(BASE_DIR, "openassessment", "conf", "locale")]

FEATURES = {
    # Set to True to enable team-based ORA submissions.
    # See: https://openedx.atlassian.net/browse/EDUCATOR-4951
    'ENABLE_ORA_TEAM_SUBMISSIONS': False,

    # A "work-around" feature toggle meant to help in cases where some file uploads are not discoverable.
    # See: https://openedx.atlassian.net/browse/EDUCATOR-4951
    'ENABLE_ORA_ALL_FILE_URLS': False,

    # A "work-around" feature toggle meant to pull file upload data our of user state, rather than Submission records.
    # See: https://openedx.atlassian.net/browse/EDUCATOR-4951
    'ENABLE_ORA_USER_STATE_UPLOAD_DATA': False,

    # Set to True to add deanonymized usernames to ORA data report
    # See: https://openedx.atlassian.net/browse/TNL-7273
    'ENABLE_ORA_USERNAMES_ON_DATA_EXPORT': False,

    # Set to True to enable this Xblock in mobile apps.
    'ENABLE_ORA_MOBILE_SUPPORT': False,

    # Set to True to enable copying/reusing rubric data
    # See: https://openedx.atlassian.net/browse/EDUCATOR-5751
    'ENABLE_ORA_RUBRIC_REUSE': False,

    # Set to True to enable individual due date extension for ORA
    'ENABLE_ORA_DUE_DATE_EXTENSION': False,
}

# disable indexing on history_date
SIMPLE_HISTORY_DATE_INDEX = False