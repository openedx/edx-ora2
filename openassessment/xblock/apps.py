# -*- coding: utf-8 -*-
"""
openassessment.xblock Django application initialization.
"""

from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig


class OraXblockConfig(AppConfig):
    """
    Configuration for the openassessment.xblock Django application.
    """

    name = "openassessment.xblock"
    label = "openassessment.xblock"
    app_label = "openassessment.xblock"

    plugin_app = {}
