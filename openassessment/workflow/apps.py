# -*- coding: utf-8 -*-
"""
openassessment.workflow Django application initialization.
"""

from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig


class OraWorkflowConfig(AppConfig):
    """
    Configuration for the openassessment.workflow Django application.
    """

    name = 'openassessment.workflow'
    label = "workflow"
    app_label = "workflow"

    plugin_app = {}
