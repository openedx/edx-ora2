"""
View-level tests for Studio view of OpenAssessment XBlock.
"""

import copy
import datetime as dt
import json
from unittest.mock import MagicMock, patch, Mock

from ddt import ddt, file_data
import pytz

from .base import XBlockHandlerTestCase, scenario


@ddt
class StudioViewTest(XBlockHandlerTestCase):
    """
    Test the view and handlers for editing the OpenAssessment XBlock in Studio.
    """
    UPDATE_EDITOR_DATA = {
        "title": "Test title",
        "text_response": "required",
        "file_upload_response": None,
        "prompts": [{"description": "Test prompt"}],
        "prompts_type": "html",
        "feedback_prompt": "Test feedback prompt",
        "feedback_default_text": "Test feedback default text",
        "submission_start": "4014-02-10T09:46",
        "submission_due": "4014-02-27T09:46",
        "file_upload_type": None,
        "white_listed_file_types": '',
        "allow_multiple_files": True,
        "show_rubric_during_response": False,
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

    ASSESSMENT_CSS_IDS = {
        "peer-assessment": "oa_peer_assessment_editor",
        "self-assessment": "oa_self_assessment_editor",
        "student-training": "oa_student_training_editor",
        "staff-assessment": "oa_staff_assessment_editor",
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.waffle_course_flag_patcher = patch(
            'openassessment.xblock.config_mixin.import_course_waffle_flag'
        )
        cls.waffle_course_flag_patcher.start()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.waffle_course_flag_patcher.stop()

    @scenario('data/basic_scenario.xml')
    def test_default_fields(self, xblock):
        # Default value should not be empty
        self.assertEqual(xblock.fields['title'].default, "Open Response Assessment")

    @scenario('data/basic_scenario.xml')
    def test_render_studio_view(self, xblock):
        self._mock_teamsets(xblock)
        frag = self.runtime.render(xblock, 'studio_view')
        self.assertTrue(frag.body_html().find('openassessment-edit'))

    @scenario('data/student_training.xml')
    def test_render_studio_with_training(self, xblock):
        self._mock_teamsets(xblock)
        frag = self.runtime.render(xblock, 'studio_view')
        self.assertTrue(frag.body_html().find('openassessment-edit'))

    @file_data('data/update_xblock.json')
    @scenario('data/basic_scenario.xml')
    def test_update_editor_context(self, xblock, data):
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False
        resp = self.request(xblock, 'update_editor_context', json.dumps(data), response_format='json')
        self.assertTrue(resp['success'], msg=resp.get('msg'))

    @scenario('data/basic_scenario.xml')
    def test_include_leaderboard_in_editor(self, xblock):
        self._mock_teamsets(xblock)
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
            "staff-assessment",
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

    @scenario('data/basic_scenario.xml')
    def test_update_editor_context_saves_teams_enabled(self, xblock):
        data = copy.deepcopy(self.UPDATE_EDITOR_DATA)
        data['teams_enabled'] = True
        ts_id = 'selected_teamsetid'
        data['selected_teamset_id'] = ts_id
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False
        resp = self.request(xblock, 'update_editor_context', json.dumps(data), response_format='json')
        self.assertTrue(resp['success'], msg=resp.get('msg'))
        self.assertTrue(xblock.teams_enabled)
        self.assertEqual(ts_id, xblock.selected_teamset_id)

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

    @scenario('data/basic_scenario_html_prompts_type.xml')
    def test_update_context_with_prompts_type(self, xblock):

        data = copy.deepcopy(self.UPDATE_EDITOR_DATA)
        data['prompts_type'] = 'text'
        xblock.runtime.modulestore = MagicMock()
        xblock.runtime.modulestore.has_published_version.return_value = False
        resp = self.request(xblock, 'update_editor_context', json.dumps(data), response_format='json')
        self.assertTrue(resp['success'], msg=resp.get('msg'))

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
        self.assertCountEqual(xblock.rubric_assessments, old_assessments)
        self.assertCountEqual(xblock.rubric_criteria, old_criteria)

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
        self._mock_teamsets(xblock)
        # Expect that the editor uses the order defined by the problem.
        self._assert_rendered_editor_order(xblock, [
            'student-training',
            'self-assessment',
            'peer-assessment',
            'staff-assessment'
        ])

        # Change the order (simulates what would happen when the author saves).
        xblock.editor_assessments_order = [
            'student-training',
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
            'peer-assessment',
            'self-assessment',
            'staff-assessment',
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
            in self.ASSESSMENT_CSS_IDS.items()
        ]
        actual_assessment_order = [
            index_dict['name']
            for index_dict in sorted(assessment_indices, key=lambda d: d['index'])
            if index_dict['index'] > 0
        ]
        self.assertEqual(actual_assessment_order, expected_assessment_order)

    @scenario('data/basic_scenario.xml')
    def test_editor_context_assigns_labels(self, xblock):
        self._mock_teamsets(xblock)
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

    @scenario('data/basic_scenario.xml')
    def test_render_studio_with_teamset_names(self, xblock):
        self._mock_teamsets(xblock)
        frag = self.runtime.render(xblock, 'studio_view')
        self.assertTrue(frag.body_html().find('teamset_name_a'))
        self.assertTrue(frag.body_html().find('teamset_id_a'))

    @scenario('data/basic_scenario.xml')
    def test_get_teamsets(self, xblock):
        xblock.xmodule_runtime = Mock(
            course_id='test_course',
            anonymous_student_id='test_student',
        )
        xblock.runtime = Mock()
        mock_teams_config = Mock(
            teamsets=[Mock(name="tset1"), Mock(name="tset2")]
        )
        mock_team_configuration_service = Mock()
        mock_team_configuration_service.get_teams_configuration.return_value = mock_teams_config
        xblock.runtime.service.return_value = mock_team_configuration_service

        teamsets = xblock.get_teamsets("test_course")
        self.assertEqual([ts.name for ts in teamsets], [ts.name for ts in mock_teams_config.teamsets])

    def _mock_teamsets(self, xblock):
        """
        Bare bones mock to allow rendering tests to function as before
        """
        xblock.get_teamsets = Mock()
        xblock.get_teamsets.return_value = [
            Mock(name="teamset_name_a", teamset_id='teamset_id_a'),
            Mock(name="teamset_name_b", teamset_id='teamset_id_b'),
        ]
