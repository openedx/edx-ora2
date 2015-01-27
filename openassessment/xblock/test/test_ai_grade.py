"""
Integration test for example-based assessment (AI).
"""
import json
import mock
from django.test.utils import override_settings
from submissions import api as sub_api
from openassessment.xblock.openassessmentblock import OpenAssessmentBlock
from .base import XBlockHandlerTestCase, scenario


class AIAssessmentIntegrationTest(XBlockHandlerTestCase):
    """
    Integration test for example-based assessment (AI).
    """
    SUBMISSION = json.dumps({'submission': ('This is submission part 1!', 'This is submission part 2!')})
    AI_ALGORITHMS = {
        'fake': 'openassessment.assessment.worker.algorithm.FakeAIAlgorithm'
    }

    @mock.patch.object(OpenAssessmentBlock, 'is_admin', new_callable=mock.PropertyMock)
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @scenario('data/example_based_only.xml', user_id='Bob')
    def test_asynch_generate_score(self, xblock, mock_is_admin):
        # Test that AI grading, which creates assessments asynchronously,
        # updates the workflow so students can receive a score.
        mock_is_admin.return_value = True

        # Train classifiers for the problem
        self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')

        # Submit a response
        self.request(xblock, 'submit', self.SUBMISSION, response_format='json')

        # BEFORE viewing the grade page, check that we get a score
        score = sub_api.get_score(xblock.get_student_item_dict())
        self.assertIsNot(score, None)
        self.assertEqual(score['submission_uuid'], xblock.submission_uuid)

    @mock.patch.object(OpenAssessmentBlock, 'is_admin', new_callable=mock.PropertyMock)
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @scenario('data/feedback_only_criterion_ai.xml', user_id='Bob')
    def test_feedback_only_criterion(self, xblock, mock_is_admin):
        # Test that AI grading, which creates assessments asynchronously,
        # updates the workflow so students can receive a score.
        mock_is_admin.return_value = True

        # Train classifiers for the problem and submit a response
        self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')
        self.request(xblock, 'submit', self.SUBMISSION, response_format='json')

        # Render the grade page
        resp = self.request(xblock, 'render_grade', json.dumps({}))
        self.assertIn('example-based', resp.lower())
