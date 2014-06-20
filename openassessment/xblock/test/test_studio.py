"""
View-level tests for Studio view of OpenAssessment XBlock.
"""

import json
import datetime as dt
import lxml.etree as etree
import mock
import pytz
from ddt import ddt, data, file_data
from openassessment.xblock.xml import UpdateFromXmlError
from .base import scenario, XBlockHandlerTestCase


@ddt
class StudioViewTest(XBlockHandlerTestCase):
    """
    Test the view and handlers for editing the OpenAssessment XBlock in Studio.
    """

    @scenario('data/basic_scenario.xml')
    def test_render_studio_view(self, xblock):
        frag = self.runtime.render(xblock, 'studio_view')
        self.assertTrue(frag.body_html().find('openassessment-edit'))

    @scenario('data/basic_scenario.xml')
    def test_get_editor_context(self, xblock):
        resp = self.request(xblock, 'editor_context', '""', response_format='json')
        self.assertTrue(resp['success'])
        self.assertEqual(resp['msg'], u'')

        # Verify that the Rubric XML is parse-able and the root is <rubric>
        rubric = etree.fromstring(resp['rubric'])
        self.assertEqual(rubric.tag, 'rubric')

        # Verify that every assessment in the list of assessments has a name.
        for assessment_dict in resp['assessments']:
            self.assertTrue(assessment_dict.get('name', False))
            if assessment_dict.get('name') == 'student-training':
                examples = etree.fromstring(assessment_dict['examples'])
                self.assertEqual(examples.tag, 'examples')

    @mock.patch('openassessment.xblock.xml.serialize_rubric_to_xml_str')
    @scenario('data/basic_scenario.xml')
    def test_get_editor_context_error(self, xblock, mock_rubric_serializer):
        # Simulate an unexpected error while serializing the XBlock
        mock_rubric_serializer.side_effect = UpdateFromXmlError('Test error!')

        # Check that we get a failure message
        resp = self.request(xblock, 'editor_context', '""', response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn(u'unexpected error', resp['msg'].lower())

    @file_data('data/update_xblock.json')
    @scenario('data/basic_scenario.xml')
    def test_update_xblock(self, xblock, data):
        # First, parse XML data into a single string.
        data['rubric'] = "".join(data['rubric'])
        xblock.published_date = None
        # Test that we can update the xblock with the expected configuration.
        request = json.dumps(data)

        # Verify the response is successfully
        resp = self.request(xblock, 'update_editor_context', request, response_format='json')
        print "ERROR IS {}".format(resp['msg'])
        self.assertTrue(resp['success'])
        self.assertIn('success', resp['msg'].lower())

        # Check that the XBlock fields were updated
        # We don't need to be exhaustive here, because we have other unit tests
        # that verify this extensively.
        self.assertEqual(xblock.title, data['title'])
        self.assertEqual(xblock.prompt, data['prompt'])
        self.assertEqual(xblock.rubric_assessments[0]['name'], data['expected-assessment'])
        self.assertEqual(xblock.rubric_criteria[0]['prompt'], data['expected-criterion-prompt'])

    @file_data('data/update_xblock.json')
    @scenario('data/basic_scenario.xml')
    def test_update_context_post_release(self, xblock, data):
        # First, parse XML data into a single string.
        data['rubric'] = "".join(data['rubric'])

        # XBlock start date defaults to already open,
        # so we should get an error when trying to update anything that change the number of points
        request = json.dumps(data)

        # Verify the response is successfully
        resp = self.request(xblock, 'update_editor_context', request, response_format='json')
        self.assertFalse(resp['success'])

    @file_data('data/invalid_update_xblock.json')
    @scenario('data/basic_scenario.xml')
    def test_update_context_invalid_request_data(self, xblock, data):
        # First, parse XML data into a single string.
        if 'rubric' in data:
            data['rubric'] = "".join(data['rubric'])

        xblock.published_date = None

        resp = self.request(xblock, 'update_editor_context', json.dumps(data), response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn(data['expected_error'], resp['msg'].lower())

    @file_data('data/invalid_rubric.json')
    @scenario('data/basic_scenario.xml')
    def test_update_rubric_invalid(self, xblock, data):
        # First, parse XML data into a single string.
        data['rubric'] = "".join(data['rubric'])

        request = json.dumps(data)

        # Store old XBlock fields for later verification
        old_title = xblock.title
        old_prompt = xblock.prompt
        old_assessments = xblock.rubric_assessments
        old_criteria = xblock.rubric_criteria

        # Verify the response fails
        resp = self.request(xblock, 'update_editor_context', request, response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn("not valid", resp['msg'].lower())

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
