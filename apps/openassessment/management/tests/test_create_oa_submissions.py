"""
Tests for the management command that creates dummy submissions.
"""

from submissions import api as sub_api
from openassessment.assessment import peer_api, self_api
from openassessment.management.commands import create_oa_submissions
from django.test import TestCase


class CreateSubmissionsTest(TestCase):

    def test_create_submissions(self):

        # Create some submissions
        cmd = create_oa_submissions.Command()
        cmd.handle("test_course", "test_item", "5")

        self.assertEqual(len(cmd.student_items), 5)
        for student_item in cmd.student_items:

            # Check that the student item was created for the right course / item
            self.assertEqual(student_item['course_id'], 'test_course')
            self.assertEqual(student_item['item_id'], 'test_item')

            # Check that a submission was created
            submissions = sub_api.get_submissions(student_item)
            self.assertEqual(len(submissions), 1)
            self.assertGreater(len(submissions[0]['answer']), 0)

            # Check that peer and self assessments were created
            assessments = peer_api.get_assessments(submissions[0]['uuid'])

            # Verify that the assessments exist and have content
            # TODO: currently peer_api.get_assessments() returns both peer- and self-assessments
            # When this call gets split, we'll need to update the test
            self.assertEqual(len(assessments), cmd.NUM_PEER_ASSESSMENTS + 1)

            for assessment in assessments:
                self.assertGreater(assessment['points_possible'], 0)

            # Check that a self-assessment was created
            submission, assessment = self_api.get_submission_and_assessment(submissions[0]['uuid'])

            # Verify that the assessment exists and has content
            self.assertIsNot(submission, None)
            self.assertIsNot(assessment, None)
            self.assertGreater(assessment['points_possible'], 0)
