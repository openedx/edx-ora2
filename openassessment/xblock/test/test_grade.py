# -*- coding: utf-8 -*-
"""
Tests for grade handlers in Open Assessment XBlock.
"""
import copy
import ddt
import json
import mock
from django.test.utils import override_settings

from submissions import api as submissions_api
from openassessment.workflow import api as workflow_api
from openassessment.assessment.api import self as self_api
from openassessment.assessment.api import peer as peer_api
from openassessment.xblock.openassessmentblock import OpenAssessmentBlock

from .base import (
    scenario, SubmitAssessmentsMixin, XBlockHandlerTestCase,
    PEER_ASSESSMENTS, SELF_ASSESSMENT, STAFF_GOOD_ASSESSMENT, STAFF_BAD_ASSESSMENT,
)


@ddt.ddt
class TestGrade(XBlockHandlerTestCase, SubmitAssessmentsMixin):
    """
    View-level tests for the XBlock grade handlers.
    """
    AI_ALGORITHMS = {
        'fake': 'openassessment.assessment.worker.algorithm.FakeAIAlgorithm'
    }

    @scenario('data/grade_scenario.xml', user_id='Greggs')
    def test_render_grade(self, xblock):
        # Submit, assess, and render the grade view
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        # Verify that feedback from each scorer appears in the view
        self.assertIn(u'єאςєɭɭєภՇ ฬ๏гк!', resp.decode('utf-8'))
        self.assertIn(u'Good job!', resp.decode('utf-8'))

        # Verify that student submission is in the view
        self.assertIn(self.SUBMISSION[1], resp.decode('utf-8'))

        # Verify that the submission and peer steps show that we're graded
        # This isn't strictly speaking part of the grade step rendering,
        # but we've already done all the setup to get to this point in the flow,
        # so we might as well verify it here.
        resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        self.assertIn('response', resp.lower())
        self.assertIn('complete', resp.lower())

        # Verify that student submission is in the view
        self.assertIn(self.SUBMISSION[1], resp.decode('utf-8'))

        resp = self.request(xblock, 'render_peer_assessment', json.dumps(dict()))
        self.assertIn('peer', resp.lower())
        self.assertIn('complete', resp.lower())

        resp = self.request(xblock, 'render_self_assessment', json.dumps(dict()))
        self.assertIn('self', resp.lower())
        self.assertIn('complete', resp.lower())

    @scenario('data/grade_scenario_self_only.xml', user_id='Greggs')
    def test_render_grade_self_only(self, xblock):
        # Submit, assess, and render the grade view
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, [], [], SELF_ASSESSMENT,
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
        peer_assessments = copy.deepcopy(PEER_ASSESSMENTS)
        for asmnt in peer_assessments:
            asmnt['criterion_feedback'] = {
                u'𝖋𝖊𝖊𝖉𝖇𝖆𝖈𝖐 𝖔𝖓𝖑𝖞': u"Ṫḧïṡ ïṡ ṡöṁë ḟëëḋḅäċḳ."
            }

        self_assessment = copy.deepcopy(SELF_ASSESSMENT)
        self_assessment['criterion_feedback'] = {
            u'𝖋𝖊𝖊𝖉𝖇𝖆𝖈𝖐 𝖔𝖓𝖑𝖞': "Feedback here",
            u'Form': 'lots of feedback yes"',
            u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': "such feedback"
        }

        # Submit, assess, and render the grade view
        self.create_submission_and_assessments(
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
        self.create_submission_and_assessments(
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
    def test_render_grade_feedback(self, xblock):
        # Submit, assess, and render the grade view
        submission = self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
        )
        workflow_info = xblock.get_workflow_info()

        # Submit a staff assessment
        self.submit_staff_assessment(xblock, submission, assessment=STAFF_GOOD_ASSESSMENT)

        # Get the grade details
        _, context = xblock.render_grade_complete(workflow_info)
        grade_details = context['grade_details']

        # Verify feedback for the first criteria
        first_criteria_assessments = grade_details['criteria'][0]['assessments']
        self.assertEqual(
            first_criteria_assessments[0]['feedback'],
            u'Staff: ฝﻉɭɭ ɗѻกﻉ!'
        )
        self.assertEqual(
            [assessment['feedback'] for assessment in first_criteria_assessments[1]['individual_assessments']],
            [
                u'Peer 2: ฝﻉɭɭ ɗѻกﻉ!',
                u'Peer 1: ฝﻉɭɭ ɗѻกﻉ!',
            ]
        )
        self.assertEqual(
            first_criteria_assessments[2]['feedback'],
            u'Peer 1: ฝﻉɭɭ ɗѻกﻉ!'
        )

        # Verify the feedback for the second criteria
        second_criteria_assessments = grade_details['criteria'][1]['assessments']
        self.assertEqual(
            second_criteria_assessments[0]['feedback'],
            u'Staff: ƒαιя נσв'
        )
        self.assertEqual(
            [assessment['feedback'] for assessment in second_criteria_assessments[1]['individual_assessments']],
            [
                u'Peer 2: ƒαιя נσв',
                u'',
            ]
        )

        # Verify the additional feedback
        additional_feedback = grade_details['additional_feedback']
        self.assertEqual(
            additional_feedback[0]['feedback'],
            u'Staff: good job!'
        )
        self.assertEqual(
            [assessment['feedback'] for assessment in additional_feedback[1]['individual_assessments']],
            [
                u'Good job!',
                u'єאςєɭɭєภՇ ฬ๏гк!',
            ]
        )

        # Integration test: verify that all of the feedback makes it to the rendered template
        html = self.request(xblock, 'render_grade', json.dumps(dict())).decode('utf-8')
        for expected_text in [
            u'Staff: ฝﻉɭɭ ɗѻกﻉ!',
            u'Peer 1: ฝﻉɭɭ ɗѻกﻉ!',
            u'Peer 2: ฝﻉɭɭ ɗѻกﻉ!',
            u'Staff: ƒαιя נσв',
            u'Peer 2: ƒαιя נσв',
            u'Staff: good job!',
            u'Good job!',
            u'єאςєɭɭєภՇ ฬ๏гк!',
        ]:
            self.assertIn(expected_text, html)

    @scenario('data/feedback_per_criterion.xml', user_id='Bernard')
    def test_render_grade_details(self, xblock):
        # Submit, assess, and render the grade view
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
        )

        # Get the grade details
        _, context = xblock.render_grade_complete(xblock.get_workflow_info())
        criteria = context['grade_details']['criteria']

        # Verify that the median peer grades are correct
        self.assertEquals(criteria[0]['assessments'][0]['option']['label'], u'Ġööḋ / ﻉซƈﻉɭɭﻉกՇ')
        self.assertEquals(criteria[1]['assessments'][0]['option']['label'], u'Fair / Good')
        self.assertEquals(criteria[0]['assessments'][0]['points'], 3)
        self.assertEquals(criteria[1]['assessments'][0]['points'], 3)

        # Verify that the self assessment grades are correct and have no points
        self.assertEquals(criteria[0]['assessments'][1]['option']['label'], u'ﻉซƈﻉɭɭﻉกՇ')
        self.assertEquals(criteria[1]['assessments'][1]['option']['label'], u'Fair')
        self.assertIsNone(criteria[0]['assessments'][1].get('points', None))
        self.assertIsNone(criteria[1]['assessments'][1].get('points', None))

    @ddt.data(
        (STAFF_GOOD_ASSESSMENT, [4, 3]),
        (STAFF_BAD_ASSESSMENT, [1, 1]),
    )
    @ddt.unpack
    @scenario('data/feedback_per_criterion.xml', user_id='Bernard')
    def test_render_staff_grades(self, xblock, assessment, scores):
        # Submit, assess, and render the grade view
        submission = self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
        )
        workflow_info = xblock.get_workflow_info()

        # Submit a staff assessment
        self.submit_staff_assessment(xblock, submission, assessment=assessment)

        # Get the grade details
        _, context = xblock.render_grade_complete(workflow_info)
        grade_details = context['grade_details']

        # Verify that the scores are correct
        for criterion_index, criterion in enumerate(grade_details['criteria']):
            for assessment_index, assessment in enumerate(criterion['assessments']):
                if assessment_index == 0:
                    self.assertEquals(assessment['points'], scores[criterion_index])
                else:
                    self.assertIsNone(assessment.get('points', None))

    @scenario('data/grade_scenario.xml', user_id='Bernard')
    def test_peer_update_after_override(self, xblock):
        # We need to copy most of the logic in self.create_submission_and_assessments here, so
        # as to delay the subitting of peer assessments to the right point in time for this test.

        # Create a submission from the user
        student_item = xblock.get_student_item_dict()
        student_id = student_item['student_id']
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Create submissions and assessments from other users
        deferred_peer_assessment = None
        for scorer_name, assessment in zip(self.PEERS, PEER_ASSESSMENTS):

            # Create a submission for each scorer for the same problem
            scorer = copy.deepcopy(student_item)
            scorer['student_id'] = scorer_name

            scorer_sub = submissions_api.create_submission(scorer, {'text': self.SUBMISSION})
            workflow_api.create_workflow(scorer_sub['uuid'], self.STEPS)

            submission = peer_api.get_submission_to_assess(scorer_sub['uuid'], len(self.PEERS))

            # Create assessments of the user's submission, unless it's the last peer
            # in that case, defer the assessment submission to later
            if scorer_name != self.PEERS[-1]:
                peer_api.create_assessment(
                    scorer_sub['uuid'], scorer_name,
                    assessment['options_selected'],
                    assessment['criterion_feedback'],
                    assessment['overall_feedback'],
                    {'criteria': xblock.rubric_criteria},
                    xblock.get_assessment_module('peer-assessment')['must_be_graded_by']
                )
            else:
                deferred_peer_assessment = (lambda:
                    peer_api.create_assessment(
                        scorer_sub['uuid'], self.PEERS[-1],
                        PEER_ASSESSMENTS[-1]['options_selected'],
                        PEER_ASSESSMENTS[-1]['criterion_feedback'],
                        PEER_ASSESSMENTS[-1]['overall_feedback'],
                        {'criteria': xblock.rubric_criteria},
                        xblock.get_assessment_module('peer-assessment')['must_be_graded_by']
                    )
                )

        # Have our user make assessments
        for assessment in PEER_ASSESSMENTS:
            peer_api.get_submission_to_assess(submission['uuid'], len(self.PEERS))
            peer_api.create_assessment(
                submission['uuid'],
                student_id,
                assessment['options_selected'],
                assessment['criterion_feedback'],
                assessment['overall_feedback'],
                {'criteria': xblock.rubric_criteria},
                xblock.get_assessment_module('peer-assessment')['must_be_graded_by']
            )

        # Have the user submit a self-assessment
        self_api.create_assessment(
            submission['uuid'], student_id, SELF_ASSESSMENT['options_selected'],
            SELF_ASSESSMENT['criterion_feedback'], SELF_ASSESSMENT['overall_feedback'],
            {'criteria': xblock.rubric_criteria}
        )

        # Submit a staff assessment
        self.submit_staff_assessment(xblock, submission, assessment=STAFF_GOOD_ASSESSMENT)

        # Get the grade details
        workflow_info = xblock.get_workflow_info()
        _, context = xblock.render_grade_complete(workflow_info)
        grade_details = context['grade_details']

        # This list comprehension is a complicated way of saying "Give me the median score from peer assessments for each criterion"
        peer_scores =   [
                            [
                                assessment['option']
                                for assessment in criterion['assessments']
                                if assessment['title'] == u'Peer Median Grade'
                            ]
                            for criterion in grade_details['criteria']
                        ]
        print peer_scores

        # Submit final peer grade
        deferred_peer_assessment()

        # Verify that peer grade is updated despite problem already having been marked 'done'
        _, context = xblock.render_grade_complete(workflow_info)
        grade_details = context['grade_details']
        updated_peer_scores =   [
                                    [
                                        assessment['option']
                                        for assessment in criterion['assessments']
                                        if assessment['title'] == u'Peer Median Grade'
                                    ]
                                    for criterion in grade_details['criteria']
                                ]
        print updated_peer_scores
        self.assertTrue(False)

    @scenario('data/grade_scenario.xml', user_id='Bob')
    def test_assessment_does_not_match_rubric(self, xblock):
         # Get to the grade complete section
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
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
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT,
            waiting_for_peer=data["waiting_for_peer"]
        )
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))

        # Verify that we're on the waiting template
        self.assertIn(data["expected_response"], resp.decode('utf-8').lower())

    @scenario('data/grade_incomplete_scenario.xml', user_id='Bunk')
    def test_grade_incomplete_missing_self(self, xblock):
        resp = self._test_incomplete_helper(xblock, [self.PEERS[0]], None)
        self.assertNotIn('peer assessment', resp)
        self.assertIn('self assessment', resp)

    @scenario('data/grade_incomplete_scenario.xml', user_id='Bunk')
    def test_grade_incomplete_missing_peer(self, xblock):
        resp = self._test_incomplete_helper(xblock, [], SELF_ASSESSMENT)
        self.assertNotIn('self assessment', resp)
        self.assertIn('peer assessment', resp)

    @scenario('data/grade_incomplete_scenario.xml', user_id='Bunk')
    def test_grade_incomplete_missing_both(self, xblock):
        resp = self._test_incomplete_helper(xblock, [], None)
        self.assertIn('self assessment', resp)
        self.assertIn('peer assessment', resp)

    def _test_incomplete_helper(self, xblock, peers, self_assessment):
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, peers, [PEER_ASSESSMENTS[0]] if peers else [], self_assessment
        )

        # Verify grading page is rendered properly
        resp = self.request(xblock, 'render_grade', json.dumps(dict()))
        self.assertIn(u'not completed', resp.decode('utf-8').lower())

        # Verify that response_submitted page is rendered properly. This isn't super tightly connnected
        # to grade rendering, but it seems a shame to do the same setup in 2 different places.
        submitted_resp = self.request(xblock, 'render_submission', json.dumps(dict()))
        decoded_response = submitted_resp.decode('utf-8').lower()
        self.assertIn(u'steps are complete and your response is fully assessed', decoded_response)
        self.assertIn(u'you still need to complete', decoded_response)
        return decoded_response

    @scenario('data/grade_scenario.xml', user_id='Greggs')
    def test_submit_feedback(self, xblock):
        # Create submissions and assessments
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
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
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
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
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
        )

        # Options should be a list, not a string
        payload = json.dumps({
            'feedback_text': u'I disliked my assessment',
            'feedback_options': u'should be a list!',
        })
        resp = self.request(xblock, 'submit_feedback', payload, response_format='json', use_runtime=False)
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
        self.create_submission_and_assessments(
            xblock, self.SUBMISSION, self.PEERS, PEER_ASSESSMENTS, SELF_ASSESSMENT
        )

        # Verify that criteria and options are assigned labels before
        # being passed to the Django template.
        # Remember the criteria and option labels so we can verify
        # that the same labels are applied to the assessment parts.
        __, context = xblock.render_grade_complete(xblock.get_workflow_info())
        criterion_labels = {}
        option_labels = {}
        for criterion in context['grade_details']['criteria']:
            self.assertEqual(criterion['label'], criterion['name'])
            criterion_labels[criterion['name']] = criterion['label']
            for option in criterion['options']:
                self.assertEqual(option['label'], option['name'])
                option_labels[(criterion['name'], option['name'])] = option['label']

            # Verify that assessment part options are also assigned labels
            for assessment in criterion['assessments']:
                expected_criterion_label = criterion_labels[assessment['criterion']['name']]
                self.assertEqual(assessment['criterion']['label'], expected_criterion_label)
                expected_option_label = option_labels[(assessment['criterion']['name'], assessment['option']['name'])]
                self.assertEqual(assessment['option']['label'], expected_option_label)
