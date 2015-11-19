"""
View-level tests for Studio view of OpenAssessment XBlock.
"""

import copy
import json
import datetime as dt
import pytz
from ddt import ddt, file_data
from mock import MagicMock
from .base import scenario, XBlockHandlerTestCase


@ddt
class StudioViewTest(XBlockHandlerTestCase):
    """
    Test the view and handlers for editing the OpenAssessment XBlock in Studio.
    """
    UPDATE_EDITOR_DATA = {
        "title": "Test title",
        "prompts": [{"description": "Test prompt"}],
        "feedback_prompt": "Test feedback prompt",
        "feedback_default_text": "Test feedback default text",
        "submission_start": "4014-02-10T09:46",
        "submission_due": "4014-02-27T09:46",
        "file_upload_type": None,
        "white_listed_file_types": '',
        "allow_latex": False,
        "leaderboard_show": 4,
        "assessments": [{"name": "self-assessment"}],
        "editor_assessments_order": [
            "student-training",
            "peer-assessment",
            "self-assessment",
        ],
        "criteria": [
            {
                "order_num": 0,
                "name": "Test criterion",
                "label": "Test criterion",
                "prompt": "Test criterion prompt",
                "feedback": "disabled",
                "options": [
                    {
                        "order_num": 0,
                        "points": 0,
                        "name": "Test option",
                        "label": "Test option",
                        "explanation": "Test explanation"
                    }
                ]
            },
        ]
    }

    RUBRIC_CRITERIA = [
        {
            "order_num": 0,
            "name": "0",
            "label": "Test criterion with no name",
            "prompt": "Test criterion prompt",
            "feedback": "disabled",
            "options": [
                {
                    "order_num": 0,
                    "points": 0,
                    "name": "0",
                    "label": "Test option with no name",
                    "explanation": "Test explanation"
                }
            ]
        },
        {
            "order_num": 1,
            "label": "Test criterion that already has a name",
            "name": "1",
            "prompt": "Test criterion prompt",
            "feedback": "disabled",
            "options": [
                {
                    "order_num": 0,
                    "points": 0,
                    "name": "0",
                    "label": "Test option with no name",
                    "explanation": "Test explanation"
                },
                {
                    "order_num": 1,
                    "points": 0,
                    "label": "Test option that already has a name",
                    "name": "1",
                    "explanation": "Test explanation"
                },
            ]
        }
    ]

    EXAMPLE_BASED_ASSESSMENT_EXAMPLES = '<examples>' + \
        '<example>' + \
            '<answer> TEST ANSWER </answer>' + \
            '<select criterion="Test criterion" option="Test option" />' + \
        '</example>' + \
    '</examples>'

    ASSESSMENT_CSS_IDS = {
        "example-based-assessment": "oa_ai_assessment_editor",
        "peer-assessment": "oa_peer_assessment_editor",
        "self-assessment": "oa_self_assessment_editor",
        "student-training": "oa_student_training_editor"
    }

    @scenario('data/basic_scenario.xml')
    def test_render_studio_view(self, xblock):
        frag = self.runtime.render(xblock, 'studio_view')
        self.assertTrue(frag.body_html().find('openassessment-edit'))

    @scenario('data/student_training.xml')
    def test_render_studio_with_training(self, xblock):
        frag = self.runtime.render(xblock, 'studio_view')
        self.assertTrue(frag.body_html().find('openassessment-edit'))

    @scenario('data/example_based_only.xml')
    def test_render_studio_with_ai(self, xblock):
        frag = self.runtime.render(xblock, 'studio_view')
        self.assertTrue('ai_assessment_settings_editor' in frag.body_html())

    @file_data('data/update_xblock.json')
    @scenario('data/basic_scenario.xml')
    def test_update_editor_context(self, xblock, data):
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False
        resp = self.request(xblock, 'update_editor_context', json.dumps(data), response_format='json')
        self.assertTrue(resp['success'], msg=resp.get('msg'))

    @scenario('data/basic_scenario.xml')
    def test_include_leaderboard_in_editor(self, xblock):
        xblock.leaderboard_show = 15
        self.assertEqual(xblock.editor_context()['leaderboard_show'], 15)

    @scenario('data/basic_scenario.xml')
    def test_update_editor_context_saves_assessment_order(self, xblock):
        # Update the XBlock with a different editor assessment order
        data = copy.deepcopy(self.UPDATE_EDITOR_DATA)
        data['editor_assessments_order'] = [
            "student-training",
            "peer-assessment",
            "self-assessment",
        ]
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False
        resp = self.request(xblock, 'update_editor_context', json.dumps(data), response_format='json')
        self.assertTrue(resp['success'], msg=resp.get('msg'))
        self.assertEqual(xblock.editor_assessments_order, data['editor_assessments_order'])

    @scenario('data/basic_scenario.xml')
    def test_update_editor_context_saves_assessment_order_with_ai(self, xblock):
        # Update the XBlock with a different editor assessment order
        data = copy.deepcopy(self.UPDATE_EDITOR_DATA)
        data['assessments'] = [{
            'name': 'example-based-assessment',
            'examples_xml': self.EXAMPLE_BASED_ASSESSMENT_EXAMPLES
        }]
        data['editor_assessments_order'] = [
            "example-based-assessment",
            "student-training",
            "peer-assessment",
            "self-assessment",
            ]
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False
        resp = self.request(xblock, 'update_editor_context', json.dumps(data), response_format='json')
        self.assertTrue(resp['success'], msg=resp.get('msg'))
        self.assertEqual(xblock.editor_assessments_order, data['editor_assessments_order'])

    @scenario('data/basic_scenario.xml')
    def test_update_editor_context_saves_leaderboard(self, xblock):
        data = copy.deepcopy(self.UPDATE_EDITOR_DATA)
        data['leaderboard_show'] = 42
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False
        resp = self.request(xblock, 'update_editor_context', json.dumps(data), response_format='json')
        self.assertTrue(resp['success'], msg=resp.get('msg'))
        self.assertEqual(xblock.leaderboard_show, 42)

    @file_data('data/invalid_update_xblock.json')
    @scenario('data/basic_scenario.xml')
    def test_update_context_invalid_request_data(self, xblock, data):
        # All schema validation errors have the same error message, so use that as the default
        # Remove the expected error from the dictionary so we don't get an unexpected key error.
        if 'expected_error' in data:
            expected_error = data.pop('expected_error')
        else:
            expected_error = 'error updating xblock configuration'

        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False
        resp = self.request(xblock, 'update_editor_context', json.dumps(data), response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn(expected_error, resp['msg'].lower())

    @file_data('data/invalid_rubric.json')
    @scenario('data/basic_scenario.xml')
    def test_update_rubric_invalid(self, xblock, data):
        request = json.dumps(data)

        # Store old XBlock fields for later verification
        old_title = xblock.title
        old_prompts = xblock.prompts
        old_assessments = xblock.rubric_assessments
        old_criteria = xblock.rubric_criteria

        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False

        # Verify the response fails
        resp = self.request(xblock, 'update_editor_context', request, response_format='json')
        self.assertFalse(resp['success'])
        self.assertIn("error updating xblock configuration", resp['msg'].lower())

        # Check that the XBlock fields were NOT updated
        # We don't need to be exhaustive here, because we have other unit tests
        # that verify this extensively.
        self.assertEqual(xblock.title, old_title)
        self.assertEqual(xblock.prompts, old_prompts)
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
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False
        xblock.start = dt.datetime(3000, 1, 1).replace(tzinfo=pytz.utc)
        resp = self.request(xblock, 'check_released', json.dumps(""), response_format='json')
        self.assertTrue(resp['success'])
        self.assertFalse(resp['is_released'])
        self.assertIn('msg', resp)

    @scenario('data/self_then_peer.xml')
    def test_render_editor_assessment_order(self, xblock):
        # Initially, the editor assessment order should be the default
        # (because we haven't set it yet by saving in Studio)
        # However, the assessment order IS set when we import the problem from XML,
        # and it differs from the default order (self->peer instead of peer->self)
        # Expect that the editor uses the order defined by the problem.
        self._assert_rendered_editor_order(xblock, [
            'example-based-assessment',
            'student-training',
            'self-assessment',
            'peer-assessment',
        ])

        # Change the order (simulates what would happen when the author saves).
        xblock.editor_assessments_order = [
            'student-training',
            'example-based-assessment',
            'peer-assessment',
            'self-assessment',
        ]
        xblock.rubric_assessments = [
            xblock.get_assessment_module('peer-assessment'),
            xblock.get_assessment_module('self-assessment'),
        ]

        # Expect that the rendered view reflects the new order
        self._assert_rendered_editor_order(xblock, [
            'student-training',
            'example-based-assessment',
            'peer-assessment',
            'self-assessment',
        ])

    def _assert_rendered_editor_order(self, xblock, expected_assessment_order):
        """
        Render the XBlock Studio editor view and verify that the
        assessments were listed in a particular order.

        Args:
            xblock (OpenAssessmentBlock)
            expected_assessment_order (list of string): The list of assessment names,
                in the order we expect.

        Raises:
            AssertionError

        """
        rendered_html = self.runtime.render(xblock, 'studio_view').body_html()
        assessment_indices = [
            {
                "name": asmnt_name,
                "index": rendered_html.find(asmnt_css_id)
            }
            for asmnt_name, asmnt_css_id
            in self.ASSESSMENT_CSS_IDS.iteritems()
        ]
        actual_assessment_order = [
            index_dict['name']
            for index_dict in sorted(assessment_indices, key=lambda d: d['index'])
        ]
        self.assertEqual(actual_assessment_order, expected_assessment_order)

    @scenario('data/basic_scenario.xml')
    def test_editor_context_assigns_labels(self, xblock):
        # Strip out any labels from criteria/options that may have been imported.
        for criterion in xblock.rubric_criteria:
            if 'label' in criterion:
                del criterion['label']
            for option in criterion['options']:
                if 'label' in option:
                    del option['label']

        # Retrieve the context used to render the Studio view
        context = xblock.editor_context()

        # Verify that labels were assigned for all criteria and options
        for criterion in context['criteria']:
            self.assertEqual(criterion['label'], criterion['name'])
            for option in criterion['options']:
                self.assertEqual(option['label'], option['name'])

        # Verify the same thing for the training example template
        for criterion in context['assessments']['training']['template']['criteria']:
            self.assertEqual(criterion['label'], criterion['name'])
            for option in criterion['options']:
                self.assertEqual(option['label'], option['name'])

        # Verify the same thing for the context for student training examples
        for example in context['assessments']['training']['examples']:
            for criterion in example['criteria']:
                self.assertEqual(criterion['label'], criterion['name'])
                for option in criterion['options']:
                    self.assertEqual(option['label'], option['name'])
