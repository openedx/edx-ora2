# -*- coding: utf-8 -*-
"""
Tests for course items listing handlers.
"""

import json

from mock import patch
from .base import scenario, XBlockHandlerTestCase, SubmitAssessmentsMixin


class TestCourseItemsListingHandlers(XBlockHandlerTestCase, SubmitAssessmentsMixin):
    """
    Test for course items listing handlers.
    """

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_non_staff_access(self, xblock):
        """
        Test non-staff access for endpoint that return items statistics

        """
        response = self.request(xblock, 'get_ora2_responses', json.dumps({}),
                                request_method='GET')
        self.assertIn('You do not have permission', response)

    @scenario('data/basic_scenario.xml', user_id='Bob')
    def test_staff_access(self, xblock):
        """
        Test staff access for endpoint that return items statistics

        """
        self.set_staff_access(xblock)
        xblock.xmodule_runtime.course_id = 'test_course'

        return_data = [{'id': 'test_1', 'title': 'title_1'},
                       {'id': 'test_2', 'title': 'title_2'}]
        with patch("openassessment.data.OraAggregateData.collect_ora2_responses", return_value=return_data):
            response = self.request(xblock, 'get_ora2_responses', json.dumps({}),
                                    request_method='GET', response_format='json')
            self.assertEqual(response, return_data)
