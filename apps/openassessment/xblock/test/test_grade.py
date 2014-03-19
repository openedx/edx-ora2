# -*- coding: utf-8 -*-
"""
Tests for grade handlers in Open Assessment XBlock.
"""
import copy
import json
from submissions import api as sub_api
from openassessment.workflow import api as workflow_api
from openassessment.assessment import peer_api, self_api
from .base import XBlockHandlerTestCase, scenario


class TestGrade(XBlockHandlerTestCase):
    """
    View-level tests for the XBlock grade handlers.
    """

    PEERS = ['McNulty', 'Moreland']

    ASSESSMENTS = [
        {
            'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
            'feedback': u'єאςєɭɭєภՇ ฬ๏гк!',
        },
        {
            'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
            'feedback': u'Good job!',
        },
    ]

    SUBMISSION = u'ՇﻉรՇ รપ๒๓ٱรรٱѻก'

    @scenario('data/grade_scenario.xml', user_id='Greggs')
    def test_render_grade(self, xblock):
        # Submit, assess, and render the grade view
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, self.ASSESSMENTS, self.ASSESSMENTS[0]
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        # Verify that feedback from each scorer appears in the view
        self.assertIn(u'єאςєɭɭєภՇ ฬ๏гк!', resp.decode('utf-8'))
        self.assertIn(u'Good job!', resp.decode('utf-8'))

    @scenario('data/grade_scenario.xml', user_id='Greggs')
    def test_submit_feedback(self, xblock):
        # Create submissions and assessments
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, self.ASSESSMENTS, self.ASSESSMENTS[0]
        )

        # Submit feedback on the assessments
        payload = json.dumps({
            'feedback_text': u'I disliked my assessment',
            'feedback_options': [u'Option 1', u'Option 2'],
        })
        resp = self.request(xblock, 'submit_feedback', payload, response_format='json')
        self.assertTrue(resp['success'])

        # Verify that the feedback was created in the database
        feedback = peer_api.get_assessment_feedback(xblock.submission_uuid)
        self.assertIsNot(feedback, None)
        self.assertEqual(feedback['feedback_text'], u'I disliked my assessment')
        self.assertItemsEqual(
            feedback['options'], [{'text': u'Option 1'}, {'text': u'Option 2'}]
        )

    @scenario('data/grade_scenario.xml', user_id='Bob')
    def test_submit_feedback_no_options(self, xblock):
        # Create submissions and assessments
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, self.ASSESSMENTS, self.ASSESSMENTS[0]
        )

        # Submit feedback on the assessments with no options specified
        payload = json.dumps({
            'feedback_text': u'I disliked my assessment',
            'feedback_options': [],
        })
        resp = self.request(xblock, 'submit_feedback', payload, response_format='json')
        self.assertTrue(resp['success'])

        # Verify that the feedback was created in the database
        feedback = peer_api.get_assessment_feedback(xblock.submission_uuid)
        self.assertIsNot(feedback, None)
        self.assertItemsEqual(feedback['options'], [])

    @scenario('data/grade_scenario.xml', user_id='Bob')
    def test_submit_feedback_invalid_options(self, xblock):
        # Create submissions and assessments
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, self.ASSESSMENTS, self.ASSESSMENTS[0]
        )

        # Options should be a list, not a string
        payload = json.dumps({
            'feedback_text': u'I disliked my assessment',
            'feedback_options': u'should be a list!',
        })
        resp = self.request(xblock, 'submit_feedback', payload, response_format='json')
        self.assertFalse(resp['success'])
        self.assertGreater(len(resp['msg']), 0)

    def _create_submission_and_assessments(self, xblock, submission_text, peers, peer_assessments, self_assessment):
        """
        Create a submission and peer/self assessments, so that the user can receive a grade.

        Args:
            xblock (OpenAssessmentBlock): The XBlock, loaded for the user who needs a grade.
            submission_text (unicode): Text of the submission from the user.
            peers (list of unicode): List of user IDs of peers who will assess the user.
            peer_assessments (list of dict): List of assessment dictionaries for peer assessments.
            self_assessment (dict): Dict of assessment for self-assessment.

        Returns:
            None
        """
        # Create a submission from the user
        student_item = xblock.get_student_item_dict()
        student_id = student_item['student_id']
        submission = xblock.create_submission(student_item, submission_text)

        # Create submissions and assessments from other users
        scorer_submissions = []
        for scorer_name, assessment in zip(peers, peer_assessments):

            # Create a submission for each scorer for the same problem
            scorer = copy.deepcopy(student_item)
            scorer['student_id'] = scorer_name

            scorer_sub = sub_api.create_submission(scorer, {'text': submission_text})
            workflow_api.create_workflow(scorer_sub['uuid'])

            submission = peer_api.get_submission_to_assess(scorer, len(peers))

            # Store the scorer's submission so our user can assess it later
            scorer_submissions.append(scorer_sub)

            # Create an assessment of the user's submission
            peer_api.create_assessment(
                submission['uuid'], scorer_name,
                assessment, {'criteria': xblock.rubric_criteria}
            )

        # Have our user make assessments (so she can get a score)
        for asmnt in peer_assessments:
            new_submission = peer_api.get_submission_to_assess(student_item, len(peers))
            peer_api.create_assessment(
                new_submission['uuid'], student_id, asmnt, {'criteria': xblock.rubric_criteria}
            )

        # Have the user submit a self-assessment (so she can get a score)
        self_api.create_assessment(
            submission['uuid'], student_id, self_assessment['options_selected'],
            {'criteria': xblock.rubric_criteria}
        )
