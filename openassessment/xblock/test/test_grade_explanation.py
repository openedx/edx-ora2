# -*- coding: utf-8 -*-
"""
Tests for grade explanation in Open Response Assessment XBlock.
"""
from __future__ import absolute_import

import json

from .base import (PEER_ASSESSMENTS, SELF_ASSESSMENT, STAFF_GOOD_ASSESSMENT,
                   SubmitAssessmentsMixin, XBlockHandlerTestCase, scenario)


class TestGradeExplanation(XBlockHandlerTestCase, SubmitAssessmentsMixin):
    """
    Tests for grade explanation in Open Response Assessment XBlock.
    """

    @scenario('data/grade_scenario_self_only.xml', user_id='Greggs')
    def test_render_grade_explanation_self_only(self, xblock):
        # Submit, assess, and render the grade view
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, [], [], SELF_ASSESSMENT,
            waiting_for_peer=True
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        self.assertIn('The grade for this problem is determined by your Self Assessment.', resp.decode('utf-8'))

    @scenario('data/grade_scenario_staff_only.xml', user_id='Bernard')
    def test_render_explanation_grade_staff_only(self, xblock):
        student_item = xblock.get_student_item_dict()
        submission = xblock.create_submission(student_item, self.SUBMISSION)
        assessment = STAFF_GOOD_ASSESSMENT

        self.submit_staff_assessment(xblock, submission, assessment)

        resp = self.request(xblock, 'render_grade', json.dumps(dict()))
        self.assertIn('The grade for this problem is determined by your Staff Grade.', resp.decode('utf-8'))

    @scenario('data/grade_scenario_peer_only.xml', user_id='Bernard')
    def test_render_grade_explanation_peer_only(self, xblock):
        # Submit, assess, and render the grade view
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, None
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        self.assertIn(
            'The grade for this problem is determined by the average overall score of your Peer Assessments.',
            resp.decode('utf-8')
        )

    @scenario('data/grade_scenario.xml', user_id='Bernard')
    def test_render_grade_explanation_self_and_peer(self, xblock):
        # Submit, assess, and render the grade view
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT,
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        self.assertIn(
            'The grade for this problem is determined by the average overall score of your Peer Assessments.',
            resp.decode('utf-8')
        )

    @scenario('data/grade_scenario_self_staff.xml', user_id='Bernard')
    def test_render_grade_explanation_self_and_staff(self, xblock):
        # Submit, assess, and render the grade view
        submission = self.create_submission_and_assessments(
            xblock, self.SUBMISSION, [], [], SELF_ASSESSMENT
        )
        assessment = STAFF_GOOD_ASSESSMENT

        self.submit_staff_assessment(xblock, submission, assessment)

        resp = self.request(xblock, 'render_grade', json.dumps(dict()))
        self.assertIn('The grade for this problem is determined by your Staff Grade.', resp.decode('utf-8'))

    @scenario('data/grade_scenario_staff_peer.xml', user_id='Bernard')
    def test_render_grade_explanation_staff_and_peer(self, xblock):
        # Submit, assess, and render the grade view
        submission = self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, None
        )
        assessment = STAFF_GOOD_ASSESSMENT

        self.submit_staff_assessment(xblock, submission, assessment)

        resp = self.request(xblock, 'render_grade', json.dumps(dict()))
        self.assertIn('The grade for this problem is determined by your Staff Grade.', resp.decode('utf-8'))

    @scenario('data/grade_scenario_self_staff_peer.xml', user_id='Greggs')
    def test_render_grade_explanation_self_staff_and_peer(self, xblock):
        # Submit, assess, and render the grade view
        submission = self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
        )
        assessment = STAFF_GOOD_ASSESSMENT

        self.submit_staff_assessment(xblock, submission, assessment)

        resp = self.request(xblock, 'render_grade', json.dumps(dict()))
        self.assertIn('The grade for this problem is determined by your Staff Grade.', resp.decode('utf-8'))
