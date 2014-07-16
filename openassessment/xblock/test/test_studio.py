"""
View-level tests for Studio view of OpenAssessment XBlock.
"""

import json
import datetime as dt
import pytz
from ddt import ddt, file_data
from .base import scenario, XBlockHandlerTestCase
import xml.etree.ElementTree as etree


@ddt
class StudioViewTest(XBlockHandlerTestCase):
    """
    Test the view and handlers for editing the OpenAssessment XBlock in Studio.
    """

    @scenario('data/basic_scenario.xml')
    def test_render_studio_view(self, xblock):
        frag = self.runtime.render(xblock, 'studio_view')
        self.assertTrue(frag.body_html().find('openassessment-edit'))

    @file_data('data/update_xblock.json')
    @scenario('data/basic_scenario.xml')
    def test_update_context(self, xblock, data):
        xblock.published_date = None
        resp = self.request(xblock, 'update_editor_context', json.dumps(data), response_format='json')
        self.assertTrue(resp['success'], msg=resp.get('msg'))

    @file_data('data/invalid_update_xblock.json')
    @scenario('data/basic_scenario.xml')
    def test_update_context_invalid_request_data(self, xblock, data):
        # All schema validation errors have the same error message, so use that as the default
        # Remove the expected error from the dictionary so we don't get an unexpected key error.
        if 'expected_error' in data:
            expected_error = data.pop('expected_error')
        else:
            expected_error = 'error updating xblock configuration'

        xblock.published_date = None
        resp = self.request(xblock, 'update_editor_context', json.dumps(data), response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn(expected_error, resp['msg'].lower())

    @file_data('data/invalid_rubric.json')
    @scenario('data/basic_scenario.xml')
    def test_update_rubric_invalid(self, xblock, data):
        request = json.dumps(data)

        # Store old XBlock fields for later verification
        old_title = xblock.title
        old_prompt = xblock.prompt
        old_assessments = xblock.rubric_assessments
        old_criteria = xblock.rubric_criteria

        # Verify the response fails
        resp = self.request(xblock, 'update_editor_context', request, response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn("error updating xblock configuration", resp['msg'].lower())

        # Check that the XBlock fields were NOT updated
        # We don't need to be exhaustive here, because we have other unit tests
        # that verify this extensively.
        self.assertEqual(xblock.title, old_title)
        self.assertEqual(xblock.prompt, old_prompt)
        self.assertItemsEqual(xblock.rubric_assessments, old_assessments)
        self.assertItemsEqual(xblock.rubric_criteria, old_criteria)

    @scenario('data/basic_scenario.xml')
    def test_check_released(self, xblock):
        # By default, the problem should be released
        resp = self.request(xblock, 'check_released', json.dumps(""), response_format='json')
        self.assertTrue(resp['success'])
        self.assertTrue(resp['is_released'])
        self.assertIn('msg', resp)

        # Set the problem to unpublished with a start date in the future
        xblock.published_date = None
        xblock.start = dt.datetime(3000, 1, 1).replace(tzinfo=pytz.utc)
        resp = self.request(xblock, 'check_released', json.dumps(""), response_format='json')
        self.assertTrue(resp['success'])
        self.assertFalse(resp['is_released'])
        self.assertIn('msg', resp)

    @scenario('data/example_based_assessment.xml')
    def test_assessment_module_ordering_example_based(self, xblock):
        self.assert_assessment_order_(xblock)

    @scenario('data/basic_scenario.xml')
    def test_assessment_module_ordering_basic(self, xblock):
        self.assert_assessment_order_(xblock)

    @scenario('data/self_then_peer.xml')
    def test_assessment_module_ordering_self_peer(self, xblock):
        self.assert_assessment_order_(xblock)

    @scenario('data/student_training.xml')
    def test_assessment_module_ordering_student_training(self, xblock):
        self.assert_assessment_order_(xblock)

    @scenario('data/self_only_scenario.xml')
    def test_assessment_module_ordering_self_only(self, xblock):
        self.assert_assessment_order_(xblock)

    def assert_assessment_order_(self, xblock):
        """
        Asserts that the assessment module editors are rendered in the correct order.
        Renders the Studio View, and then examines the html body for the tags that we anticipate
        to be in the tag for each editor, and compare the order. If it is anything besides
        strictly increasing, we say that they rendered in the incorrect order.
        """
        frag = self.runtime.render(xblock, 'studio_view')
        frag = frag.body_html()

        assessments_in_order = self._find_assessment_order(xblock)

        assessment_indicies = [frag.find(assessment) for assessment in assessments_in_order]

        # Asserts that for any pairwise comparison of elements n and n-1 in the lookup of indicies
        # the value at n will be greater than n-1 (i.e. the place we find one ID is after the one before it)
        self.assertTrue(
            all(a < b for a, b in zip(assessment_indicies, assessment_indicies[1:]))
        )

    def _find_assessment_order(self, xblock):
        """
        Finds the order that we anticipate HTML ID tags of the section editors within the settings editor.

        Returns:
            A list with the four setting editor IDs, in the the order that we would anticipate given
            the Xblock's problem definition that is handed in.
        """
        assessments = []
        for assessment in xblock.rubric_assessments:
            assessments.append(assessment['name'].replace('-', '_'))

        all_assessments = {'student_training', 'peer_assessment', 'self_assessment', 'example_based_assessment'}
        unused_assessments = list(all_assessments - set(assessments))
        assessments.extend(unused_assessments)

        id_dictionary = {
            "example_based_assessment": "oa_ai_assessment_editor",
            "peer_assessment": "oa_peer_assessment_editor",
            "self_assessment": "oa_self_assessment_editor",
            "student_training": "oa_student_training_editor"
        }
        return [id_dictionary[name] for name in assessments]