"""
View-level tests for Studio view of OpenAssessment XBlock.
"""

import json
import datetime as dt
import lxml.etree as etree
import mock
import pytz
from ddt import ddt, data
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
    def test_get_xml(self, xblock):
        resp = self.request(xblock, 'xml', '""', response_format='json')
        self.assertTrue(resp['success'])
        self.assertEqual(resp['msg'], u'')

        # Verify that the XML is parseable and the root is <openassessment>
        root = etree.fromstring(resp['xml'])
        self.assertEqual(root.tag, 'openassessment')

    @mock.patch('openassessment.xblock.studio_mixin.serialize_content')
    @scenario('data/basic_scenario.xml')
    def test_get_xml_error(self, xblock, mock_serialize):
        # Simulate an unexpected error while serializing the XBlock
        mock_serialize.side_effect = ValueError('Test error!')

        # Check that we get a failure message
        resp = self.request(xblock, 'xml', '""', response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn(u'unexpected error', resp['msg'].lower())

    @scenario('data/basic_scenario.xml')
    def test_update_xml(self, xblock):

        # Set the XBlock's release date to the future,
        # so we are not restricted in what we can edit
        xblock.start = dt.datetime(3000, 1, 1).replace(tzinfo=pytz.utc)

        request = json.dumps({'xml': self.load_fixture_str('data/updated_block.xml')})

        # Verify the response is successfully
        resp = self.request(xblock, 'update_xml', request, response_format='json')
        self.assertTrue(resp['success'])
        self.assertIn('success', resp['msg'].lower())

        # Check that the XBlock fields were updated
        # We don't need to be exhaustive here, because we have other unit tests
        # that verify this extensively.
        self.assertEqual(xblock.title, u'Foo')
        self.assertEqual(xblock.prompt, u'Test prompt')
        self.assertEqual(xblock.rubric_assessments[0]['name'], 'peer-assessment')
        self.assertEqual(xblock.rubric_criteria[0]['prompt'], 'Test criterion prompt')

    @scenario('data/basic_scenario.xml')
    def test_update_xml_post_release(self, xblock):

        # XBlock start date defaults to already open,
        # so we should get an error when trying to update anything that change the number of points
        request = json.dumps({'xml': self.load_fixture_str('data/updated_block.xml')})

        # Verify the response is successfully
        resp = self.request(xblock, 'update_xml', request, response_format='json')
        self.assertFalse(resp['success'])

    @scenario('data/basic_scenario.xml')
    def test_update_xml_invalid_request_data(self, xblock):
        resp = self.request(xblock, 'update_xml', json.dumps({}), response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn('xml', resp['msg'].lower())

    @scenario('data/basic_scenario.xml')
    def test_update_xml_invalid_date_format(self, xblock):
        request = json.dumps({'xml': self.load_fixture_str('data/invalid_dates.xml')})
        resp = self.request(xblock, 'update_xml', request, response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn("cannot be later than", resp['msg'].lower())

    # Test that we enforce that there are exactly two assessments,
    # peer ==> self
    # If and when we remove this restriction, this test can be deleted.
    @scenario('data/basic_scenario.xml')
    def test_update_xml_invalid_assessment_combo(self, xblock):
        request = json.dumps({'xml': self.load_fixture_str('data/invalid_assessment_combo.xml')})
        resp = self.request(xblock, 'update_xml', request, response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn("must have exactly two assessments", resp['msg'].lower())

    @data(('data/invalid_rubric.xml', 'rubric'), ('data/invalid_assessment.xml', 'assessment'))
    @scenario('data/basic_scenario.xml')
    def test_update_xml_invalid(self, xblock, data):
        xml_path = data[0]
        expected_msg = data[1]

        request = json.dumps({'xml': self.load_fixture_str(xml_path)})

        # Store old XBlock fields for later verification
        old_title = xblock.title
        old_prompt = xblock.prompt
        old_assessments = xblock.rubric_assessments
        old_criteria = xblock.rubric_criteria

        # Verify the response fails
        resp = self.request(xblock, 'update_xml', request, response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn(expected_msg, resp['msg'].lower())

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
