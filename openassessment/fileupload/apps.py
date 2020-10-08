# -*- coding: utf-8 -*-
"""
openassessment.fileupload Django application initialization.
"""

from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig


class OraFileuploadConfig(AppConfig):
    """
    Configuration for the openassessment.fileupload Django application.
    """

    name = 'openassessment.fileupload'
    label = "openassessment.fileupload"
    app_label = "openassessment.fileupload"

    plugin_app = {
        'url_config': {
            'lms.djangoapp': {
                'namespace': '',
                'regex': '^openassessment/fileupload/',
                'relative_path': 'urls',
            },
            'cms.djangoapp': {
                'namespace': '',
                'regex': '^openassessment/fileupload/',
                'relative_path': 'urls',
            },
        },
    }
