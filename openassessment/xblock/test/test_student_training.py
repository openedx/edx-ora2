"""
Tests for the student training step in the Open Assessment XBlock.
"""
import datetime
import json
import pprint
from unittest.mock import Mock, patch

import ddt
import pytz

from django.db import DatabaseError

from openassessment.assessment.models import StudentTrainingWorkflow
from openassessment.workflow import api as workflow_api
from openassessment.workflow.errors import AssessmentWorkflowError

from .base import SubmissionTestMixin, XBlockHandlerTestCase, scenario


class StudentTrainingTest(XBlockHandlerTestCase, SubmissionTestMixin):
    """
    Base class for student training tests.
    """

    def assert_path_and_context(self, xblock, expected_path, expected_context):
        """
        Render the student training step and verify that the expected template
        and context were used.  Also check that the template renders without error.

        Args:
            xblock (OpenAssessmentBlock): The XBlock under test.
            expected_path (str): The expected template path.
            expected_context (dict): The expected template context.

        Raises:
            AssertionError

        """
        path, context = xblock.training_path_and_context()

        expected_context['xblock_id'] = xblock.scope_ids.usage_id

        self.assertEqual(path, expected_path)
        self.assertEqual(len(context), len(expected_context))
        for key in expected_context.keys():
            if key == 'training_due':
                iso_date = context['training_due'].isoformat()
                self.assertEqual(iso_date, expected_context[key])
            else:
                self.assertEqual(context[key], expected_context[key])

        # Verify that we render without error
        resp = self.request(xblock, 'render_student_training', json.dumps({}))
        self.assertGreater(len(resp), 0)


@ddt.ddt
class StudentTrainingAssessTest(StudentTrainingTest):
    """
    Tests for student training assessment.
    """

    @scenario('data/student_training.xml', user_id="Plato")
    @ddt.file_data('data/student_training_mixin.json')
    def test_correct(self, xblock, data):
        self.create_test_submission(xblock)
        data["expected_context"]['user_timezone'] = None
        data["expected_context"]['user_language'] = None
        self.assert_path_and_context(xblock, data["expected_template"], data["expected_context"])

        # Agree with the course author's assessment
        # (as defined in the scenario XML)
        data = {
            'options_selected': {
                'Vocabulary': 'Good',
                'Grammar': 'Excellent'
            }
        }
        resp = self.request(xblock, 'training_assess', json.dumps(data), response_format='json')

        # Expect that we were correct
        self.assertTrue(resp['success'], msg=resp.get('msg'))
        self.assertFalse(resp['corrections'])

    @scenario('data/student_training.xml', user_id="Plato")
    @ddt.file_data('data/student_training_mixin.json')
    def test_correct_with_error(self, xblock, data):
        self.create_test_submission(xblock)
        data["expected_context"]['user_timezone'] = None
        data["expected_context"]['user_language'] = None
        self.assert_path_and_context(xblock, data["expected_template"], data["expected_context"])

        # Agree with the course author's assessment
        # (as defined in the scenario XML)
        data = {
            'options_selected': {
                'Vocabulary': 'Good',
                'Grammar': 'Excellent'
            }
        }
        with patch.object(workflow_api, "update_from_assessments") as mock_workflow_update:
            mock_workflow_update.side_effect = AssessmentWorkflowError("Oh no!")
            resp = self.request(xblock, 'training_assess', json.dumps(data), response_format='json')

            # Expect that we were not correct due to a workflow update error.
            self.assertFalse(resp['success'], msg=resp.get('msg'))
            self.assertEqual('Could not update workflow status.', resp.get('msg'))
            self.assertNotIn('corrections', resp)

    @scenario('data/student_training.xml', user_id="Plato")
    @ddt.file_data('data/student_training_mixin.json')
    def test_incorrect(self, xblock, data):
        self.create_test_submission(xblock)
        data["expected_context"]['user_timezone'] = None
        data["expected_context"]['user_language'] = None
        self.assert_path_and_context(xblock, data["expected_template"], data["expected_context"])

        # Disagree with the course author's assessment
        # (as defined in the scenario XML)
        select_data = {
            'options_selected': {
                'Vocabulary': 'Poor',
                'Grammar': 'Poor'
            }
        }
        resp = self.request(xblock, 'training_assess', json.dumps(select_data), response_format='json')

        # Expect that we were marked incorrect
        self.assertTrue(resp['success'], msg=resp.get('msg'))
        self.assertTrue(resp['corrections'])

    @scenario('data/student_training.xml', user_id="Plato")
    @ddt.file_data('data/student_training_mixin.json')
    def test_updates_workflow(self, xblock, data):
        expected_context = data["expected_context"].copy()
        expected_template = data["expected_template"]
        self.create_test_submission(xblock)
        expected_context['user_timezone'] = None
        expected_context['user_language'] = None
        self.assert_path_and_context(xblock, expected_template, expected_context)

        # Agree with the course author's assessment
        # (as defined in the scenario XML)
        selected_data = {
            'options_selected': {
                'Vocabulary': 'Good',
                'Grammar': 'Excellent'
            }
        }
        resp = self.request(xblock, 'training_assess', json.dumps(selected_data), response_format='json')

        # Expect that we were correct
        self.assertTrue(resp['success'], msg=resp.get('msg'))
        self.assertFalse(resp['corrections'])

        # Agree with the course author's assessment
        # (as defined in the scenario XML)
        selected_data = {
            'options_selected': {
                'Vocabulary': 'Excellent',
                'Grammar': 'Poor'
            }
        }

        expected_context["training_num_completed"] = 1
        expected_context["training_num_current"] = 2
        expected_context["training_essay"] = {
            'answer': {
                'parts': [{
                    'text': "тєѕт αηѕωєя",
                    'prompt': {
                        'description':
                            'Given the state of the world today, what do you think should be done to combat poverty?'
                    }
                }]
            }
        }

        self.assert_path_and_context(xblock, expected_template, expected_context)
        resp = self.request(xblock, 'training_assess', json.dumps(selected_data), response_format='json')

        # Expect that we were correct
        self.assertTrue(resp['success'], msg=resp.get('msg'))
        self.assertFalse(resp['corrections'])
        expected_context = {
            "allow_multiple_files": True,
            "allow_latex": False,
            'prompts_type': 'text',
            'user_timezone': None,
            'user_language': None
        }
        expected_template = "legacy/student_training/student_training_complete.html"
        self.assert_path_and_context(xblock, expected_template, expected_context)

    @scenario('data/feedback_only_criterion_student_training.xml', user_id='Bob')
    def test_feedback_only_criterion(self, xblock):
        self.create_test_submission(xblock)
        self.request(xblock, 'render_student_training', json.dumps({}))

        # Agree with the course author's assessment
        # (as defined in the scenario XML)
        # We do NOT pass in an option for the feedback-only criterion,
        # because it doesn't have any options.
        data = {
            'options_selected': {
                'vocabulary': 'good',
            }
        }
        resp = self.request(xblock, 'training_assess', json.dumps(data), response_format='json')

        # Expect that we were correct
        self.assertTrue(resp['success'], msg=resp.get('msg'))
        self.assertFalse(resp['corrections'])

    @scenario('data/student_training.xml', user_id="Plato")
    @ddt.file_data('data/student_training_mixin.json')
    def test_request_error(self, xblock, data):
        self.create_test_submission(xblock)
        expected_context = data["expected_context"].copy()
        expected_template = data["expected_template"]
        expected_context['user_timezone'] = None
        expected_context['user_language'] = None

        self.assert_path_and_context(xblock, expected_template, expected_context)
        resp = self.request(xblock, 'training_assess', json.dumps({}), response_format='json')
        self.assertFalse(resp['success'], msg=resp.get('msg'))

        selected_data = {
            'options_selected': "foo"
        }
        resp = self.request(xblock, 'training_assess', json.dumps(selected_data), response_format='json')
        self.assertFalse(resp['success'], msg=resp.get('msg'))

    @scenario('data/student_training.xml', user_id="Plato")
    @ddt.file_data('data/student_training_mixin.json')
    def test_invalid_options_dict(self, xblock, data):
        self.create_test_submission(xblock)
        expected_context = data["expected_context"].copy()
        expected_template = data["expected_template"]
        expected_context['user_timezone'] = None
        expected_context['user_language'] = None
        self.assert_path_and_context(xblock, expected_template, expected_context)

        selected_data = {
            'options_selected': {
                'Bananas': 'Excellent',
                'Grammar': 'Poor'
            }
        }

        resp = self.request(xblock, 'training_assess', json.dumps(selected_data), response_format='json')
        self.assertFalse(resp['success'], msg=resp.get('msg'))

    @scenario('data/student_training.xml', user_id="Plato")
    def test_no_submission(self, xblock):
        selected_data = {
            'options_selected': {
                'Vocabulary': 'Excellent',
                'Grammar': 'Poor'
            }
        }
        resp = self.request(xblock, 'training_assess', json.dumps(selected_data))
        self.assertIn("Your scores could not be checked", resp.decode('utf-8'))

    def _assert_path_and_context(self, xblock, expected_path, expected_context):
        """
        Render the student training step and verify that the expected template
        and context were used.  Also check that the template renders without error.

        Args:
            xblock (OpenAssessmentBlock): The XBlock under test.
            expected_path (str): The expected template path.
            expected_context (dict): The expected template context.

        Raises:
            AssertionError

        """
        path, context = xblock.training_path_and_context()

        expected_context['xblock_id'] = xblock.scope_ids.usage_id

        self.assertEqual(path, expected_path)
        self.assertEqual(len(context), len(expected_context))
        for key in expected_context.keys():
            if key == 'training_due':
                iso_date = context['training_due'].isoformat()
                self.assertEqual(iso_date, expected_context[key])
            else:
                msg = "Expected \n {expected} \n but found \n {actual}".format(
                    actual=pprint.pformat(context[key]),
                    expected=pprint.pformat(expected_context[key])
                )
                self.assertEqual(context[key], expected_context[key], msg=msg)

            # Verify that we render without error
        resp = self.request(xblock, 'render_student_training', json.dumps({}))
        self.assertGreater(len(resp), 0)


class StudentTrainingRenderTest(StudentTrainingTest):
    """
    Tests for student training step rendering.
    """
    @scenario('data/basic_scenario.xml', user_id="Plato")
    def test_no_student_training_defined(self, xblock):
        self.create_test_submission(xblock)
        resp = self.request(xblock, 'render_student_training', json.dumps({}))
        self.assertEqual("", resp.decode('utf-8'))

    @scenario('data/student_training.xml', user_id="Plato")
    def test_no_submission(self, xblock):
        resp = self.request(xblock, 'render_student_training', json.dumps({}))
        self.assertIn("Not Available", resp.decode('utf-8'))

    @scenario('data/student_training.xml')
    def test_studio_preview(self, xblock):
        resp = self.request(xblock, 'render_student_training', json.dumps({}))
        self.assertIn("Not Available", resp.decode('utf-8'))

    @scenario('data/student_training_due.xml', user_id="Plato")
    def test_past_due(self, xblock):
        self.create_test_submission(xblock)
        expected_template = "legacy/student_training/student_training_closed.html"
        expected_context = {
            'training_due': "2000-01-01T00:00:00+00:00",
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': None,
            'user_language': None
        }
        self.assert_path_and_context(xblock, expected_template, expected_context)

    @scenario('data/student_training.xml', user_id="Plato")
    def test_cancelled_submission(self, xblock):
        submission = self.create_test_submission(xblock)
        xblock.get_workflow_info = Mock(return_value={
            'status': 'cancelled',
            'submission_uuid': submission['uuid']
        })
        expected_template = "legacy/student_training/student_training_cancelled.html"
        expected_context = {
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': None,
            'user_language': None
        }
        self.assert_path_and_context(xblock, expected_template, expected_context)

    @scenario('data/student_training.xml', user_id="Plato")
    @patch.object(StudentTrainingWorkflow, "get_workflow")
    def test_internal_error(self, xblock, mock_workflow):
        mock_workflow.side_effect = DatabaseError("Oh no.")
        self.create_test_submission(xblock)
        resp = self.request(xblock, 'render_student_training', json.dumps({}))
        self.assertIn("An unexpected error occurred.", resp.decode('utf-8'))

    @scenario('data/student_training_future.xml', user_id="Plato")
    def test_before_start(self, xblock):
        self.create_test_submission(xblock)
        expected_template = "legacy/student_training/student_training_unavailable.html"
        expected_context = {
            'training_start': datetime.datetime(3000, 1, 1).replace(tzinfo=pytz.utc),
            'allow_multiple_files': True,
            'allow_latex': False,
            'prompts_type': 'text',
            'user_timezone': None,
            'user_language': None
        }
        self.assert_path_and_context(xblock, expected_template, expected_context)
