"""
Tests for grade explanation in Open Response Assessment XBlock.
"""

import json

from unittest.mock import patch

from ddt import ddt, data

from .base import (
    PEER_ASSESSMENTS,
    SELF_ASSESSMENT,
    STAFF_GOOD_ASSESSMENT,
    SubmissionTestMixin,
    SubmitAssessmentsMixin,
    XBlockHandlerTestCase,
    scenario
)


@ddt
class TestGradeExplanation(XBlockHandlerTestCase, SubmitAssessmentsMixin, SubmissionTestMixin):
    """
    Tests for grade explanation in Open Response Assessment XBlock.
    """

    second_sentences_options = {
        "self": "The grade for this problem is determined by your Self Assessment.",
        "staff": "The grade for this problem is determined by your Staff Grade.",
        "peer": "The grade for this problem is determined by the median score of your Peer Assessments."
    }

    assessment_score_priority = (
        ('self', 'peer'),
        ('peer', 'self')
    )

    @scenario('data/grade_scenario_self_only.xml', user_id='Greggs')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_only(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            self.create_submission_and_assessments(
                xblock, self.SUBMISSION, [], [], SELF_ASSESSMENT,
                waiting_for_peer=True
            )
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["self"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_staff_only.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_explanation_grade_staff_only(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            submission = self.create_test_submission(xblock)
            self.submit_staff_assessment(xblock, submission, STAFF_GOOD_ASSESSMENT)
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["staff"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_peer_only.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_peer_only(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, None
            )
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["peer"], resp.decode('utf-8'))

    @scenario('data/grade_scenario.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_and_peer(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT,
            )
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            if assessment_score_priority.index('self') < assessment_score_priority.index('peer'):
                self.assertIn(self.second_sentences_options["self"], resp.decode('utf-8'))
            else:
                self.assertIn(self.second_sentences_options["peer"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_self_staff.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_and_staff(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            submission = self.create_submission_and_assessments(
                xblock, self.SUBMISSION, [], [], SELF_ASSESSMENT
            )
            self.submit_staff_assessment(xblock, submission, STAFF_GOOD_ASSESSMENT)
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["staff"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_staff_peer.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_staff_and_peer(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            submission = self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, None
            )
            self.submit_staff_assessment(xblock, submission, STAFF_GOOD_ASSESSMENT)
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["staff"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_self_staff_peer.xml', user_id='Greggs')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_staff_and_peer(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            submission = self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
            )
            self.submit_staff_assessment(xblock, submission, STAFF_GOOD_ASSESSMENT)
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["staff"], resp.decode('utf-8'))

    # Incomplete Assessment Grade Explanation Tests

    @scenario('data/grade_scenario_self_only.xml', user_id='Greggs')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_incomplete_assessment(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            self.create_submission_and_assessments(
                xblock, self.SUBMISSION, [], [], None,
            )
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["self"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_staff_only.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_explanation_grade_staff_incomplete_assessment(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            self.create_test_submission(xblock)
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["staff"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_peer_only.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_peer_incomplete_assessments(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, [], None
            )
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(
                'You have not yet received all necessary peer reviews to determine your final grade.',
                resp.decode('utf-8')
            )
            self.assertIn(self.second_sentences_options['peer'], resp.decode('utf-8'))

    @scenario('data/grade_scenario.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_and_peer_with_self_missing(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, None,
            )
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            if assessment_score_priority.index('self') < assessment_score_priority.index('peer'):
                self.assertIn(self.second_sentences_options["self"], resp.decode('utf-8'))
            else:
                self.assertIn(self.second_sentences_options["peer"], resp.decode('utf-8'))

    @scenario('data/grade_scenario.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_and_peer_with_peer_missing(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, [], SELF_ASSESSMENT,
            )
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            if assessment_score_priority.index('self') < assessment_score_priority.index('peer'):
                self.assertIn(self.second_sentences_options["self"], resp.decode('utf-8'))
            else:
                self.assertIn(self.second_sentences_options["peer"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_self_staff.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_and_staff_with_self_missing(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            submission = self.create_submission_and_assessments(
                xblock, self.SUBMISSION, [], [], None
            )
            self.submit_staff_assessment(xblock, submission, STAFF_GOOD_ASSESSMENT)
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["staff"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_self_staff.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_and_staff_with_staff_missing(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            self.create_submission_and_assessments(
                xblock, self.SUBMISSION, [], [], SELF_ASSESSMENT
            )
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options['staff'], resp.decode('utf-8'))

    @scenario('data/grade_scenario_staff_peer.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_staff_and_peer_with_staff_missing(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, None
            )
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["staff"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_staff_peer.xml', user_id='Bernard')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_staff_and_peer_with_peer_missing(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            submission = self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, [], None, waiting_for_peer=True
            )
            self.submit_staff_assessment(xblock, submission, STAFF_GOOD_ASSESSMENT)
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["staff"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_self_staff_peer.xml', user_id='Greggs')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_staff_and_peer_with_self_missing(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            submission = self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, None
            )
            self.submit_staff_assessment(xblock, submission, STAFF_GOOD_ASSESSMENT)
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["staff"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_self_staff_peer.xml', user_id='Greggs')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_staff_and_peer_with_staff_missing(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
            )
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["staff"], resp.decode('utf-8'))

    @scenario('data/grade_scenario_self_staff_peer.xml', user_id='Greggs')
    @data(*assessment_score_priority)
    def test_render_grade_explanation_self_staff_and_peer_with_peer_missing(self, xblock, assessment_score_priority):
        with patch(
            'openassessment.workflow.models.AssessmentWorkflow.ASSESSMENT_SCORE_PRIORITY',
            assessment_score_priority
        ):
            submission = self.create_submission_and_assessments(
                xblock, self.SUBMISSION, self.PEERS, [], SELF_ASSESSMENT
            )
            self.submit_staff_assessment(xblock, submission, STAFF_GOOD_ASSESSMENT)
            resp = self.request(xblock, 'render_grade', json.dumps({}))

            self.assertIn(self.second_sentences_options["staff"], resp.decode('utf-8'))
