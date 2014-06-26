# -*- coding: utf-8 -*-
"""
Tests for assessment models.
"""

from openassessment.test_utils import CacheResetTest
from submissions import api as sub_api
from openassessment.assessment.models import (
    AssessmentFeedback, AssessmentFeedbackOption,
    PeerWorkflow, PeerWorkflowItem
)


class AssessmentFeedbackTest(CacheResetTest):
    """
    Tests for assessment feedback.
    This is feedback that students give in response to the peer assessments they receive.
    """

    def setUp(self):
        self.feedback = AssessmentFeedback.objects.create(
            submission_uuid='test_submission',
            feedback_text='test feedback',
        )

    def test_default_options(self):
        self.assertEqual(self.feedback.options.count(), 0)

    def test_add_options_all_new(self):
        # We haven't created any feedback options yet, so these should be created.
        self.feedback.add_options(['I liked my assessment', 'I thought my assessment was unfair'])

        # Check the feedback options
        options = self.feedback.options.all()
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].text, 'I liked my assessment')
        self.assertEqual(options[1].text, 'I thought my assessment was unfair')

    def test_add_options_some_new(self):
        # Create one feedback option in the database
        AssessmentFeedbackOption.objects.create(text='I liked my assessment')

        # Add feedback options.  The one that's new should be created.
        self.feedback.add_options(['I liked my assessment', 'I thought my assessment was unfair'])

        # Check the feedback options
        options = self.feedback.options.all()
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].text, 'I liked my assessment')
        self.assertEqual(options[1].text, 'I thought my assessment was unfair')

    def test_add_options_empty(self):
        # No options
        self.feedback.add_options([])
        self.assertEqual(len(self.feedback.options.all()), 0)

        # Add an option
        self.feedback.add_options(['test'])
        self.assertEqual(len(self.feedback.options.all()), 1)

        # Add an empty list of options
        self.feedback.add_options([])
        self.assertEqual(len(self.feedback.options.all()), 1)

    def test_add_options_duplicates(self):

        # Add some options, which will be created
        self.feedback.add_options(['I liked my assessment', 'I thought my assessment was unfair'])

        # Add some more options, one of which is a duplicate
        self.feedback.add_options(['I liked my assessment', 'I disliked my assessment'])

        # There should be three options
        options = self.feedback.options.all()
        self.assertEqual(len(options), 3)
        self.assertEqual(options[0].text, 'I liked my assessment')
        self.assertEqual(options[1].text, 'I thought my assessment was unfair')
        self.assertEqual(options[2].text, 'I disliked my assessment')

        # There should be only three options in the database
        self.assertEqual(AssessmentFeedbackOption.objects.count(), 3)

    def test_add_options_all_old(self):
        # Add some options, which will be created
        self.feedback.add_options(['I liked my assessment', 'I thought my assessment was unfair'])

        # Add some more options, all of which are duplicates
        self.feedback.add_options(['I liked my assessment', 'I thought my assessment was unfair'])

        # There should be two options
        options = self.feedback.options.all()
        self.assertEqual(len(options), 2)
        self.assertEqual(options[0].text, 'I liked my assessment')
        self.assertEqual(options[1].text, 'I thought my assessment was unfair')

        # There should be two options in the database
        self.assertEqual(AssessmentFeedbackOption.objects.count(), 2)

    def test_unicode(self):
        # Create options with unicode
        self.feedback.add_options([u'𝓘 𝓵𝓲𝓴𝓮𝓭 𝓶𝔂 𝓪𝓼𝓼𝓮𝓼𝓼𝓶𝓮𝓷𝓽', u'ﾉ ｲんougんｲ ﾶﾘ ﾑ丂丂乇丂丂ﾶ乇刀ｲ wﾑ丂 u刀ｷﾑﾉ尺'])

        # There should be two options in the database
        self.assertEqual(AssessmentFeedbackOption.objects.count(), 2)


class PeerWorkflowTest(CacheResetTest):
    """
    Tests for the peer workflow model.
    """
    STUDENT_ITEM = {
        'student_id': 'test_student',
        'course_id': 'test_course',
        'item_type': 'openassessment',
        'item_id': 'test_item'
    }

    OTHER_STUDENT = {
        'student_id': 'test_student_2',
        'course_id': 'test_course',
        'item_type': 'openassessment',
        'item_id': 'test_item'
    }

    def test_create_item_multiple_available(self):
        # Bugfix TIM-572
        submitter_sub = sub_api.create_submission(self.STUDENT_ITEM, 'test answer')
        submitter_workflow = PeerWorkflow.objects.create(
            student_id=self.STUDENT_ITEM['student_id'],
            item_id=self.STUDENT_ITEM['item_id'],
            course_id=self.STUDENT_ITEM['course_id'],
            submission_uuid=submitter_sub['uuid']
        )
        scorer_sub = sub_api.create_submission(self.OTHER_STUDENT, 'test answer 2')
        scorer_workflow = PeerWorkflow.objects.create(
            student_id=self.OTHER_STUDENT['student_id'],
            item_id=self.OTHER_STUDENT['item_id'],
            course_id=self.OTHER_STUDENT['course_id'],
            submission_uuid=scorer_sub['uuid']
        )

        for _ in range(2):
            PeerWorkflowItem.objects.create(
                scorer=scorer_workflow,
                author=submitter_workflow,
                submission_uuid=submitter_sub['uuid']
            )

        # This used to cause an error when `get_or_create` returned multiple workflow items
        PeerWorkflow.create_item(scorer_workflow, submitter_sub['uuid'])
