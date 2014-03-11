"""
Tests for the management command that creates dummy submissions.
"""

import copy
from submissions import api as sub_api
from openassessment.assessment import peer_api, self_api
from django.core.management import call_command
from django.test import TestCase


class CreateScenarioTest(TestCase):

    def test_create_submission(self):
        call_command('create_oa_submission', 'test_user', 'test_course', 'test_problem')
        submissions = sub_api.get_submissions({
            'student_id': 'test_user',
            'course_id': 'test_course',
            'item_id': 'test_problem',
            'item_type': 'openassessment',
        })
        self.assertEqual(len(submissions), 1)
        self.assertGreater(len(submissions[0]['answer']), 0)

    def test_create_peer_assessments(self):

        # Create a submission with peer assessments
        call_command(
            'create_oa_submission', 'test_user', 'test_course', 'test_problem',
            num_peer_assessments=2
        )

        # Retrieve the submission
        submissions = sub_api.get_submissions({
            'student_id': 'test_user',
            'course_id': 'test_course',
            'item_id': 'test_problem',
            'item_type': 'openassessment',
        }, limit=1)
        self.assertEqual(len(submissions), 1)

        # Retrieve the peer assessments
        assessments = peer_api.get_assessments(submissions[0]['uuid'])

        # Verify that the assessments exist and have content
        self.assertEqual(len(assessments), 2)
        for assessment in assessments:
            self.assertGreater(assessment['points_possible'], 0)
            self.assertGreater(len(assessment['feedback']), 0)

    def test_create_self_assessment(self):

        # Create a submission with a self-assessment
        call_command(
            'create_oa_submission', 'test_user', 'test_course', 'test_problem',
            has_self_assessment=True
        )

        # Retrieve the submission
        submissions = sub_api.get_submissions({
            'student_id': 'test_user',
            'course_id': 'test_course',
            'item_id': 'test_problem',
            'item_type': 'openassessment',
        }, limit=1)
        self.assertEqual(len(submissions), 1)

        # Retrieve the self assessment
        submission, assessment = self_api.get_submission_and_assessment(submissions[0]['uuid'])

        # Verify that the assessment exists and has content
        self.assertIsNot(submission, None)
        self.assertIsNot(assessment, None)
        self.assertGreater(assessment['points_possible'], 0)

    def test_missing_args(self):

        full_args = ['test_user', 'test_course', 'test_problem']

        # Delete each required arg and verify that the command fails
        for index in range(len(full_args)):
            args = copy.copy(full_args)
            del args[index]

            with self.assertRaises(SystemExit) as ex:
                call_command('create_oa_submission', *args)
            self.assertEqual(ex.exception.code, 1)