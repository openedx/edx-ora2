# -*- coding: utf-8 -*-
"""
Tests for grade handlers in Open Assessment XBlock.
"""
import copy
import json
from submissions import api as sub_api
from openassessment.workflow import api as workflow_api
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from .base import XBlockHandlerTestCase, scenario


class TestGrade(XBlockHandlerTestCase):
    """
    View-level tests for the XBlock grade handlers.
    """

    PEERS = ['McNulty', 'Moreland']

    ASSESSMENTS = [
        {
            'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
            'criterion_feedback': {
                u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'Peer 1: ฝﻉɭɭ ɗѻกﻉ!'
            },
            'overall_feedback': u'єאςєɭɭєภՇ ฬ๏гк!',
        },
        {
            'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
            'criterion_feedback': {
                u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'Peer 2: ฝﻉɭɭ ɗѻกﻉ!',
                u'Form': u'Peer 2: ƒαιя נσв'
            },
            'overall_feedback': u'Good job!',
        },
    ]

    SUBMISSION = u'ՇﻉรՇ รપ๒๓ٱรรٱѻก'

    STEPS = ['peer', 'self']

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

        # Verify that the submission and peer steps show that we're graded
        # This isn't strictly speaking part of the grade step rendering,
        # but we've already done all the setup to get to this point in the flow,
        # so we might as well verify it here.
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        self.assertIn('response', resp.lower())
        self.assertIn('complete', resp.lower())

        resp = self.request(xblock, 'render_peer_assessment', json.dumps(dict()))
        self.assertIn('peer', resp.lower())
        self.assertIn('complete', resp.lower())

        resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
        self.assertIn('self', resp.lower())
        self.assertIn('complete', resp.lower())

    @scenario('data/feedback_per_criterion.xml', user_id='Bernard')
    def test_render_grade_feedback_per_criterion(self, xblock):
        # Submit, assess, and render the grade view
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, self.ASSESSMENTS, self.ASSESSMENTS[0]
        )

        # Verify that the context for the grade complete page contains the feedback
        _, context = xblock.render_grade_complete(xblock.get_workflow_info())
        criteria = context['rubric_criteria']
        self.assertEqual(criteria[0]['feedback'], [
            u'Peer 2: ฝﻉɭɭ ɗѻกﻉ!',
            u'Peer 1: ฝﻉɭɭ ɗѻกﻉ!',
        ])
        self.assertEqual(criteria[1]['feedback'], [u'Peer 2: ƒαιя נσв'])

        # The order of the peers in the per-criterion feedback needs
        # to match the order of the peer assessments
        # We verify this by checking that the first peer assessment
        # has the criteria feedback matching the first feedback
        # for each criterion.
        assessments = context['peer_assessments']
        first_peer_feedback = [part['feedback'] for part in assessments[0]['parts']]
        self.assertItemsEqual(first_peer_feedback, [u'Peer 2: ฝﻉɭɭ ɗѻกﻉ!', u'Peer 2: ƒαιя נσв'])

        # Integration test: verify that the context makes it to the rendered template
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))
        self.assertIn(u'Peer 1: ฝﻉɭɭ ɗѻกﻉ!', resp.decode('utf-8'))
        self.assertIn(u'Peer 2: ฝﻉɭɭ ɗѻกﻉ!', resp.decode('utf-8'))
        self.assertIn(u'Peer 2: ƒαιя נσв', resp.decode('utf-8'))

    @scenario('data/grade_scenario.xml', user_id='Omar')
    def test_grade_waiting(self, xblock):
        # Waiting to be assessed by a peer
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, self.ASSESSMENTS, self.ASSESSMENTS[0],
            waiting_for_peer=True
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        # Verify that we're on the waiting template
        self.assertIn(u'waiting for peer assessment', resp.decode('utf-8').lower())

    @scenario('data/grade_incomplete_scenario.xml', user_id='Bunk')
    def test_grade_incomplete_missing_self(self, xblock):
        # Graded peers, but haven't completed self assessment
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, [self.PEERS[0]], [self.ASSESSMENTS[0]], None
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        # Verify that we're on the right template
        self.assertIn(u'not completed', resp.decode('utf-8').lower())

    @scenario('data/grade_incomplete_scenario.xml', user_id='Daniels')
    def test_grade_incomplete_missing_peer(self, xblock):
        # Have not yet completed peer assessment
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, [], [], None
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        # Verify that we're on the right template
        self.assertIn(u'not completed', resp.decode('utf-8').lower())

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

    def _create_submission_and_assessments(
        self, xblock, submission_text, peers, peer_assessments, self_assessment,
        waiting_for_peer=False
    ):
        """
        Create a submission and peer/self assessments, so that the user can receive a grade.

        Args:
            xblock (OpenAssessmentBlock): The XBlock, loaded for the user who needs a grade.
            submission_text (unicode): Text of the submission from the user.
            peers (list of unicode): List of user IDs of peers who will assess the user.
            peer_assessments (list of dict): List of assessment dictionaries for peer assessments.
            self_assessment (dict): Dict of assessment for self-assessment.

        Kwargs:
            waiting_for_peer (bool): If true, skip creation of peer assessments for the user's submission.

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
            workflow_api.create_workflow(scorer_sub['uuid'], self.STEPS)

            submission = peer_api.get_submission_to_assess(scorer_sub['uuid'], len(peers))

            # Store the scorer's submission so our user can assess it later
            scorer_submissions.append(scorer_sub)

            # Create an assessment of the user's submission
            if not waiting_for_peer:
                peer_api.create_assessment(
                    scorer_sub['uuid'], scorer_name,
                    assessment['options_selected'],
                    assessment['criterion_feedback'],
                    assessment['overall_feedback'],
                    {'criteria': xblock.rubric_criteria},
                    xblock.get_assessment_module('peer-assessment')['must_be_graded_by']
                )

        # Have our user make assessments (so she can get a score)
        for asmnt in peer_assessments:
            peer_api.get_submission_to_assess(submission['uuid'], len(peers))
            peer_api.create_assessment(
                submission['uuid'],
                student_id,
                asmnt['options_selected'],
                asmnt['criterion_feedback'],
                asmnt['overall_feedback'],
                {'criteria': xblock.rubric_criteria},
                xblock.get_assessment_module('peer-assessment')['must_be_graded_by']
            )

        # Have the user submit a self-assessment (so she can get a score)
        if self_assessment is not None:
            self_api.create_assessment(
                submission['uuid'], student_id, self_assessment['options_selected'],
                {'criteria': xblock.rubric_criteria}
            )
