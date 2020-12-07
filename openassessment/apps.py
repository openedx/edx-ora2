# -*- coding: utf-8 -*-
"""
openassessment Django application initialization.
"""

from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig


class OraConfig(AppConfig):
    """
    Configuration for the openassessment Django application.
    """

    name = "openassessment"

    plugin_app = {}
