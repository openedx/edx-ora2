# -*- coding: utf-8 -*-
"""
Test OpenAssessment XBlock data_conversion.
"""

import ddt
import mock

from django.test import TestCase

from openassessment.xblock.data_conversion import (
    create_prompts_dict,
)

@ddt.ddt
class DataConversionTest(TestCase):

    @ddt.data(
        (None, [{'description': ''}]),
        ('Test prompt.', [{'description': 'Test prompt.'}]),
        ('[{"description": "Test prompt."}]', [{'description': 'Test prompt.'}]),
    )
    @ddt.unpack
    def test_create_prompts_dict(self, input, output):
        self.assertEqual(create_prompts_dict(input), output)
