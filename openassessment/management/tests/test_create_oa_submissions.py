"""
Tests for the management command that creates dummy submissions.
"""

from submissions import api as sub_api
from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.management.commands import create_oa_submissions
from django.test import TestCase


class CreateSubmissionsTest(TestCase):

    def test_create_submissions(self):

        # Create some submissions
        cmd = create_oa_submissions.Command(**{'self_assessment_required': True})
        cmd.handle("test_course", "test_item", "5", 100)
        self.assertEqual(len(cmd.student_items), 5)
        for student_item in cmd.student_items:

            # Check that the student item was created for the right course / item
            self.assertEqual(student_item['course_id'], 'test_course')
            self.assertEqual(student_item['item_id'], 'test_item')

            # Check that a submission was created
            submissions = sub_api.get_submissions(student_item)
            self.assertEqual(len(submissions), 1)

            answer_dict = submissions[0]['answer']
            self.assertIsInstance(answer_dict['text'], basestring)
            self.assertGreater(len(answer_dict['text']), 0)

            # Check that peer and self assessments were created
            assessments = peer_api.get_assessments(submissions[0]['uuid'], scored_only=False)

            # Verify that the assessments exist and have content
            self.assertEqual(len(assessments), cmd.NUM_PEER_ASSESSMENTS)

            for assessment in assessments:
                self.assertGreater(assessment['points_possible'], 0)

            # Check that a self-assessment was created
            assessment = self_api.get_assessment(submissions[0]['uuid'])

            # Verify that the assessment exists and has content
            self.assertIsNot(assessment, None)
            self.assertGreater(assessment['points_possible'], 0)
