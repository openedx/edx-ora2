# -*- coding: utf-8 -*-
"""
openassessment.assessment Django application initialization.
"""

from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig


class OraAssessmentConfig(AppConfig):
    """
    Configuration for the openassessment.assessment Django application.
    """

    name = "openassessment.assessment"
    label = "assessment"
    app_label = "assessment"

    plugin_app = {}
