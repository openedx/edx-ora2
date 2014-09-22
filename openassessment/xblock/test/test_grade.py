# -*- coding: utf-8 -*-
"""
Tests for grade handlers in Open Assessment XBlock.
"""
import copy
import ddt
import json
import mock
from django.test.utils import override_settings
from submissions import api as sub_api
from openassessment.workflow import api as workflow_api
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.xblock.openassessmentblock import OpenAssessmentBlock
from .base import XBlockHandlerTestCase, scenario


@ddt.ddt
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

    AI_ALGORITHMS = {
        'fake': 'openassessment.assessment.worker.algorithm.FakeAIAlgorithm'
    }

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

    @scenario('data/grade_scenario_track_changes.xml', user_id='Greggs')
    def test_render_grade_with_track_changes(self, xblock):
        # Submit, assess, and render the grade view
        self._create_submission_and_assessments(
            xblock,
            self.SUBMISSION,
            self.PEERS,
            self.ASSESSMENTS,
            self.ASSESSMENTS[0],
            should_track_changes=True,
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

    @scenario('data/grade_scenario_self_only.xml', user_id='Greggs')
    def test_render_grade_self_only(self, xblock):
        # Submit, assess, and render the grade view
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, [], [], self.ASSESSMENTS[0],
            waiting_for_peer=True
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        # Verify that feedback from each scorer appears in the view
        self.assertIn(u'ﻉซƈﻉɭɭﻉกՇ', resp.decode('utf-8'))
        self.assertIn(u'Fair', resp.decode('utf-8'))

        # Verify that the submission and peer steps show that we're graded
        # This isn't strictly speaking part of the grade step rendering,
        # but we've already done all the setup to get to this point in the flow,
        # so we might as well verify it here.
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        self.assertIn('response', resp.lower())
        self.assertIn('complete', resp.lower())

        resp = self.request(xblock, 'render_peer_assessment', json.dumps(dict()))
        self.assertNotIn('peer', resp.lower())
        self.assertNotIn('complete', resp.lower())

        resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
        self.assertIn('self', resp.lower())
        self.assertIn('complete', resp.lower())

    @scenario('data/feedback_only_criterion_grade.xml', user_id='Greggs')
    def test_render_grade_feedback_only_criterion(self, xblock):
        # Add in per-criterion feedback for the feedback-only criterion
        peer_assessments = copy.deepcopy(self.ASSESSMENTS)
        for asmnt in peer_assessments:
            asmnt['criterion_feedback'] = {
                u'𝖋𝖊𝖊𝖉𝖇𝖆𝖈𝖐 𝖔𝖓𝖑𝖞': u"Ṫḧïṡ ïṡ ṡöṁë ḟëëḋḅäċḳ."
            }

        self_assessment = copy.deepcopy(self.ASSESSMENTS[0])
        self_assessment['criterion_feedback'] = {
            u'𝖋𝖊𝖊𝖉𝖇𝖆𝖈𝖐 𝖔𝖓𝖑𝖞': "Feedback here",
            u'Form': 'lots of feedback yes"',
            u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': "such feedback"
        }

        # Submit, assess, and render the grade view
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, peer_assessments, self_assessment
        )

        # Render the grade section
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))
        self.assertIn('your response', resp.lower())

        # Verify that feedback from each scorer appears in the view
        self.assertIn(u'єאςєɭɭєภՇ ฬ๏гк!', resp.decode('utf-8'))
        self.assertIn(u'Good job!', resp.decode('utf-8'))

    @mock.patch.object(OpenAssessmentBlock, 'is_admin', new_callable=mock.PropertyMock)
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @scenario('data/grade_scenario_ai_only.xml', user_id='Greggs')
    def test_render_grade_ai_only(self, xblock, mock_is_admin):
        # Train classifiers using the fake AI algorithm
        mock_is_admin.return_value = True
        self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')

        # Submit, assess, and render the grade view
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, [], [], None, waiting_for_peer=True
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        # Verify that feedback from each scorer appears in the view
        self.assertNotIn(u'єאςєɭɭєภՇ', resp.decode('utf-8'))
        self.assertIn(u'Poor', resp.decode('utf-8'))

        # Verify that the submission and peer steps show that we're graded
        # This isn't strictly speaking part of the grade step rendering,
        # but we've already done all the setup to get to this point in the flow,
        # so we might as well verify it here.
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        self.assertIn('response', resp.lower())
        self.assertIn('complete', resp.lower())

        resp = self.request(xblock, 'render_peer_assessment', json.dumps(dict()))
        self.assertNotIn('peer', resp.lower())
        self.assertNotIn('complete', resp.lower())

        resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
        self.assertNotIn('self', resp.lower())
        self.assertNotIn('complete', resp.lower())

    @scenario('data/feedback_per_criterion.xml', user_id='Bernard')
    def test_render_grade_feedback_per_criterion(self, xblock):
        # Submit, assess, and render the grade view
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, self.ASSESSMENTS, self.ASSESSMENTS[0]
        )

        # Verify that the context for the grade complete page contains the feedback
        _, context = xblock.render_grade_complete(xblock.get_workflow_info())
        criteria = context['rubric_criteria']

        self.assertEqual(criteria[0]['peer_feedback'], [
            u'Peer 2: ฝﻉɭɭ ɗѻกﻉ!',
            u'Peer 1: ฝﻉɭɭ ɗѻกﻉ!',
        ])
        self.assertEqual(criteria[0]['self_feedback'], u'Peer 1: ฝﻉɭɭ ɗѻกﻉ!')
        self.assertEqual(criteria[1]['peer_feedback'], [u'Peer 2: ƒαιя נσв'])

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

    @scenario('data/grade_scenario.xml', user_id='Bob')
    def test_assessment_does_not_match_rubric(self, xblock):
         # Get to the grade complete section
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, self.ASSESSMENTS, self.ASSESSMENTS[0]
        )

        # Change the problem definition so it no longer
        # matches the assessments.  This should never happen
        # for a student (since we prevent authors from doing this post-release),
        # but it may happen if a course author has submitted
        # an assessment for a problem before it was published,
        # or if course authors mess around with course import.
        xblock.rubric_criteria[0]["name"] = "CHANGED NAME!"

        # Expect that the page renders without an error
        # It won't show the assessment criterion that changed
        # (since it's not part of the original assessment),
        # but at least it won't display an error.
        resp = self.request(xblock, 'render_grade', json.dumps({}))
        self.assertGreater(resp, 0)

    @ddt.file_data('data/waiting_scenarios.json')
    @scenario('data/grade_waiting_scenario.xml', user_id='Omar')
    def test_grade_waiting(self, xblock, data):
        # If AI classifiers are not trained, then we should see a "waiting for AI" display
        if not data["waiting_for_ai"]:
            with mock.patch.object(
                OpenAssessmentBlock, 'is_admin', new_callable=mock.PropertyMock
            ) as mock_is_admin:
                mock_is_admin.return_value = True
                self.request(xblock, 'schedule_training', json.dumps({}), response_format='json')

        # Waiting to be assessed by a peer
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, self.ASSESSMENTS, self.ASSESSMENTS[0],
            waiting_for_peer=data["waiting_for_peer"]
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        # Verify that we're on the waiting template
        self.assertIn(data["expected_response"], resp.decode('utf-8').lower())

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

    @scenario('data/grade_scenario.xml', user_id='Greggs')
    def test_grade_display_assigns_labels(self, xblock):
        # Strip out labels defined for criteria and options in the problem definition
        for criterion in xblock.rubric_criteria:
            if 'label' in criterion:
                del criterion['label']
            for option in criterion['options']:
                if 'label' in option:
                    del option['label']

        # Create a submission and assessments so we can get a grade
        self._create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, self.ASSESSMENTS, self.ASSESSMENTS[0]
        )

        # Verify that criteria and options are assigned labels before
        # being passed to the Django template.
        # Remember the criteria and option labels so we can verify
        # that the same labels are applied to the assessment parts.
        __, context = xblock.render_grade_complete(xblock.get_workflow_info())
        criterion_labels = {}
        option_labels = {}
        for criterion in context['rubric_criteria']:
            self.assertEqual(criterion['label'], criterion['name'])
            criterion_labels[criterion['name']] = criterion['label']
            for option in criterion['options']:
                self.assertEqual(option['label'], option['name'])
                option_labels[(criterion['name'], option['name'])] = option['label']

        # Verify that assessment part options are also assigned labels
        for asmnt in context['peer_assessments'] + [context['self_assessment']]:
            for part in asmnt['parts']:
                expected_criterion_label = criterion_labels[part['criterion']['name']]
                self.assertEqual(part['criterion']['label'], expected_criterion_label)
                expected_option_label = option_labels[(part['criterion']['name'], part['option']['name'])]
                self.assertEqual(part['option']['label'], expected_option_label)

    def _create_submission_and_assessments(
        self, xblock, submission_text, peers, peer_assessments, self_assessment,
        waiting_for_peer=False,
        should_track_changes=False,
    ):
        """
        Create a submission and peer/self assessments, so that the user can receive a grade.

        Args:
            xblock (OpenAssessmentBlock): The XBlock, loaded for the user who needs a grade.
            submission_text (unicode): Text of the submission from the user.
            peers (list of unicode): List of user IDs of peers who will assess the user.
            peer_assessments (list of dict): List of assessment dictionaries for peer assessments.
            self_assessment (dict): Dict of assessment for self-assessment.

        Keyword Arguments:
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

            track_changes_edits = ''
            if should_track_changes:
                track_changes_edits = submission_text + u'<span class="ins"> is wrong!</span>'

            # Create an assessment of the user's submission
            if not waiting_for_peer:
                peer_api.create_assessment(
                    scorer_sub['uuid'], scorer_name,
                    assessment['options_selected'],
                    assessment['criterion_feedback'],
                    assessment['overall_feedback'],
                    {'criteria': xblock.rubric_criteria},
                    xblock.get_assessment_module('peer-assessment')['must_be_graded_by'],
                    track_changes_edits=track_changes_edits,
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
                self_assessment['criterion_feedback'], self_assessment['overall_feedback'],
                {'criteria': xblock.rubric_criteria}
            )
