# -*- coding: utf-8 -*-
"""
Tests for the student training step in the Open Assessment XBlock.
"""
import json
from openassessment.assessment.api import student_training
from .base import XBlockHandlerTestCase, scenario


class StudentTrainingAssessTest(XBlockHandlerTestCase):
    """
    Tests for student training assessment.
    """
    SUBMISSION = {
        'submission': u'Thé őbjéćt őf édúćátíőń íś tő téáćh úś tő ĺővé ẃhát íś béáútífúĺ.'
    }

    @scenario('data/student_training.xml', user_id="Plato")
    def test_correct(self, xblock):
        xblock.create_submission(xblock.get_student_item_dict(), self.SUBMISSION)

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
        self.assertTrue(resp['correct'])

    @scenario('data/student_training.xml', user_id="Plato")
    def test_incorrect(self, xblock):
        xblock.create_submission(xblock.get_student_item_dict(), self.SUBMISSION)

        # Disagree with the course author's assessment
        # (as defined in the scenario XML)
        data = {
            'options_selected': {
                'Vocabulary': 'Poor',
                'Grammar': 'Poor'
            }
        }
        resp = self.request(xblock, 'training_assess', json.dumps(data), response_format='json')

        # Expect that we were marked incorrect
        self.assertTrue(resp['success'], msg=resp.get('msg'))
        self.assertFalse(resp['correct'])

    @scenario('data/student_training.xml', user_id="Plato")
    def test_updates_workflow(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_no_examples_left(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_request_error(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_internal_error(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_invalid_options_dict(self, xblock):
        self.fail()

    @scenario('data/basic_scenario.xml', user_id="Plato")
    def test_no_student_training_defined(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_no_submission(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_studio_preview(self, xblock):
        self.fail()

    @scenario('data/student_training.xml')
    def test_not_logged_in(self, xblock):
        self.fail()


class StudentTrainingRenderTest(XBlockHandlerTestCase):
    """
    Tests for student training step rendering.
    """

    @scenario('data/student_training_due.xml', user_id="Plato")
    def test_past_due(self, xblock):
        self.fail()

    @scenario('data/student_training_future.xml', user_id="Plato")
    def test_before_start(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_training_complete(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_training_example_available(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_no_training_examples_left(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_render_error(self, xblock):
        self.fail()

    @scenario('data/basic_scenario.xml', user_id="Plato")
    def test_no_student_training_defined(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_no_submission(self, xblock):
        self.fail()

    @scenario('data/student_training.xml', user_id="Plato")
    def test_studio_preview(self, xblock):
        self.fail()

    @scenario('data/student_training.xml')
    def test_not_logged_in(self, xblock):
        self.fail()

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
        self.assertEqual(path, expected_path)
        self.assertItemsEqual(context, expected_context)

        # Verify that we render without error
        resp = self.request(xblock, 'render_student_training', json.dumps({}))
        self.assertGreater(len(resp), 0)
