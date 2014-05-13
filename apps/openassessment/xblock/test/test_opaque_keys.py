# -*- coding: utf-8 -*-
"""
Tests for opaque key transition in the LMS runtime.
See https://github.com/edx/edx-platform/wiki/Opaque-Keys
"""
import mock
from .base import XBlockHandlerTestCase, scenario


class TestOpaqueKeys(XBlockHandlerTestCase):
    """
    Test that the XBlock handles the opaque key transition gracefully.
    """

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_opaque_key_deprecated_string(self, xblock):
        # Simulate the opaque key changeover by
        # providing a mock `to_deprecated_string()` method.
        usage_key = mock.MagicMock()
        usage_key.to_deprecated_string.return_value = u"เՇє๓ เ๔"
        course_key = mock.MagicMock()
        course_key.to_deprecated_string.return_value = u"¢συяѕє ι∂"

        xblock.scope_ids = mock.MagicMock()
        xblock.scope_ids.usage_id = usage_key

        xblock.xmodule_runtime = mock.MagicMock()
        xblock.xmodule_runtime.course_id = course_key

        student_item = xblock.get_student_item_dict()

        # Expect that we correctly serialize the opaque keys
        self.assertEqual(student_item['item_id'], u"เՇє๓ เ๔")
        self.assertEqual(student_item['course_id'], u"¢συяѕє ι∂")
