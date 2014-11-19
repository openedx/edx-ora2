# -*- coding: utf-8 -*-
"""
Tests for self-assessment API.
"""

import copy
import datetime
import pytz

from django.db import DatabaseError
from mock import patch

from openassessment.assessment.api.self import (
    create_assessment, submitter_is_finished, get_assessment
)
from openassessment.assessment.errors import SelfAssessmentInternalError, SelfAssessmentRequestError
from openassessment.test_utils import CacheResetTest
from submissions.api import create_submission


class TestSelfApi(CacheResetTest):

    STUDENT_ITEM = {
        'student_id': u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
        'item_id': 'test_item',
        'course_id': 'test_course',
        'item_type': 'test_type'
    }

    RUBRIC = {
        "criteria": [
            {
                "name": "clarity",
                "prompt": "How clear was it?",
                "options": [
                    {"name": "somewhat clear", "points": 1, "explanation": ""},
                    {"name": "clear", "points": 3, "explanation": ""},
                    {"name": "very clear", "points": 5, "explanation": ""},
                ]
            },
            {
                "name": "accuracy",
                "prompt": "How accurate was the content?",
                "options": [
                    {"name": "somewhat accurate", "points": 1, "explanation": ""},
                    {"name": "accurate", "points": 3, "explanation": ""},
                    {"name": "very accurate", "points": 5, "explanation": ""},
                ]
            },
        ]
    }

    OPTIONS_SELECTED = {
        "clarity": "clear",
        "accuracy": "very accurate",
    }

    CRITERION_FEEDBACK = {
        "clarity": "Like a morning in the restful city of San Fransisco, the piece was indescribable, beautiful, and too foggy to properly comprehend.",
        "accuracy": "Like my sister's cutting comments about my weight, I may not have enjoyed the piece, but I cannot fault it for its factual nature."
    }

    OVERALL_FEEDBACK = (
        u"Unfortunately, the nature of being is too complex to comment, judge, or discern any one"
        u"arbitrary set of things over another."
    )

    def test_create_assessment(self):
        # Initially, there should be no submission or self assessment
        self.assertEqual(get_assessment("5"), None)

        # Create a submission to self-assess
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        # Now there should be a submission, but no self-assessment
        assessment = get_assessment(submission["uuid"])
        self.assertIs(assessment, None)
        self.assertFalse(submitter_is_finished(submission['uuid'], {}))

        # Create a self-assessment for the submission
        assessment = create_assessment(
            submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
            self.OPTIONS_SELECTED, self.CRITERION_FEEDBACK, self.OVERALL_FEEDBACK, self.RUBRIC,
            scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
        )

        # Self-assessment should be complete
        self.assertTrue(submitter_is_finished(submission['uuid'], {}))

        # Retrieve the self-assessment
        retrieved = get_assessment(submission["uuid"])

        # Check that the assessment we created matches the assessment we retrieved
        # and that both have the correct values
        self.assertItemsEqual(assessment, retrieved)
        self.assertEqual(assessment['submission_uuid'], submission['uuid'])
        self.assertEqual(assessment['points_earned'], 8)
        self.assertEqual(assessment['points_possible'], 10)
        self.assertEqual(assessment['feedback'], u'' + self.OVERALL_FEEDBACK)
        self.assertEqual(assessment['score_type'], u'SE')

    def test_create_assessment_no_submission(self):
        # Attempt to create a self-assessment for a submission that doesn't exist
        with self.assertRaises(SelfAssessmentRequestError):
            create_assessment(
                'invalid_submission_uuid', u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
                self.OPTIONS_SELECTED, self.CRITERION_FEEDBACK, self.OVERALL_FEEDBACK, self.RUBRIC,
                scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
            )

    def test_create_assessment_wrong_user(self):
        # Create a submission
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        # Attempt to create a self-assessment for the submission from a different user
        with self.assertRaises(SelfAssessmentRequestError):
            create_assessment(
                'invalid_submission_uuid', u'another user',
                self.OPTIONS_SELECTED, self.CRITERION_FEEDBACK, self.OVERALL_FEEDBACK, self.RUBRIC,
                scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
            )

    def test_create_assessment_invalid_criterion_feedback(self):
        # Create a submission
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        # Mutate the criterion feedback to not include all the appropriate criteria.
        criterion_feedback = {"clarify": "not", "accurate": "sure"}

        # Attempt to create a self-assessment with criterion_feedback that do not match the rubric
        with self.assertRaises(SelfAssessmentRequestError):
            create_assessment(
                submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
                self.OPTIONS_SELECTED, criterion_feedback, self.OVERALL_FEEDBACK, self.RUBRIC,
                scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
            )

    def test_create_assessment_invalid_criterion(self):
        # Create a submission
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        # Mutate the selected option criterion so it does not match a criterion in the rubric
        options = copy.deepcopy(self.OPTIONS_SELECTED)
        options['invalid criterion'] = 'very clear'

        # Attempt to create a self-assessment with options that do not match the rubric
        with self.assertRaises(SelfAssessmentRequestError):
            create_assessment(
                submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
                options, self.CRITERION_FEEDBACK, self.OVERALL_FEEDBACK, self.RUBRIC,
                scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
            )

    def test_create_assessment_invalid_option(self):
        # Create a submission
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        # Mutate the selected option so the value does not match an available option
        options = copy.deepcopy(self.OPTIONS_SELECTED)
        options['clarity'] = 'invalid option'

        # Attempt to create a self-assessment with options that do not match the rubric
        with self.assertRaises(SelfAssessmentRequestError):
            create_assessment(
                submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
                options, self.CRITERION_FEEDBACK, self.OVERALL_FEEDBACK, self.RUBRIC,
                scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
            )

    def test_create_assessment_missing_criterion(self):
        # Create a submission
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        # Delete one of the criterion that's present in the rubric
        options = copy.deepcopy(self.OPTIONS_SELECTED)
        del options['clarity']

        # Attempt to create a self-assessment with options that do not match the rubric
        with self.assertRaises(SelfAssessmentRequestError):
            create_assessment(
                submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
                options, self.CRITERION_FEEDBACK, self.OVERALL_FEEDBACK, self.RUBRIC,
                scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
            )

    def test_create_assessment_timestamp(self):
        # Create a submission to self-assess
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        # Record the current system clock time
        before = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

        # Create a self-assessment for the submission
        # Do not override the scored_at timestamp, so it should be set to the current time
        assessment = create_assessment(
            submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
            self.OPTIONS_SELECTED, self.CRITERION_FEEDBACK, self.OVERALL_FEEDBACK, self.RUBRIC,
        )

        # Retrieve the self-assessment
        retrieved = get_assessment(submission["uuid"])

        # Expect that both the created and retrieved assessments have the same
        # timestamp, and it's >= our recorded time.
        self.assertEqual(assessment['scored_at'], retrieved['scored_at'])
        self.assertGreaterEqual(assessment['scored_at'], before)

    def test_create_multiple_self_assessments(self):
        # Create a submission to self-assess
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        # Self assess once
        assessment = create_assessment(
            submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
            self.OPTIONS_SELECTED, self.CRITERION_FEEDBACK, self.OVERALL_FEEDBACK, self.RUBRIC,
        )

        # Attempt to self-assess again, which should raise an exception
        with self.assertRaises(SelfAssessmentRequestError):
            create_assessment(
                submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
                self.OPTIONS_SELECTED, self.CRITERION_FEEDBACK, self.OVERALL_FEEDBACK, self.RUBRIC,
            )

        # Expect that we still have the original assessment
        retrieved = get_assessment(submission["uuid"])
        self.assertItemsEqual(assessment, retrieved)

    def test_is_complete_no_submission(self):
        # This submission uuid does not exist
        self.assertFalse(submitter_is_finished('abc1234', {}))

    def test_create_assessment_criterion_with_zero_options(self):
        # Create a submission to self-assess
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        # Modify the rubric to include a criterion with no options (only written feedback)
        rubric = copy.deepcopy(self.RUBRIC)
        rubric['criteria'].append({
            "name": "feedback only",
            "prompt": "feedback only",
            "options": []
        })

        criterion_feedback = copy.deepcopy(self.CRITERION_FEEDBACK)
        criterion_feedback['feedback only'] = "This is the feedback for the Zero Option Criterion."

        # Create a self-assessment for the submission
        assessment = create_assessment(
            submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
            self.OPTIONS_SELECTED, criterion_feedback, self.OVERALL_FEEDBACK, rubric,
            scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
        )

        # The self-assessment should have set the feedback for
        # the criterion with no options to an empty string
        self.assertEqual(assessment["parts"][2]["option"], None)
        self.assertEqual(assessment["parts"][2]["feedback"], u"This is the feedback for the Zero Option Criterion.")

    def test_create_assessment_all_criteria_have_zero_options(self):
        # Create a submission to self-assess
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        # Use a rubric with only criteria with no options (only written feedback)
        rubric = copy.deepcopy(self.RUBRIC)
        for criterion in rubric["criteria"]:
            criterion["options"] = []

        # Create a self-assessment for the submission
        # We don't select any options, since none of the criteria have options
        options_selected = {}

        # However, because they don't have options, they need to have criterion feedback.
        criterion_feedback = {
            'clarity': 'I thought it was about as accurate as Scrubs is to the medical profession.',
            'accuracy': 'I thought it was about as accurate as Scrubs is to the medical profession.'
        }

        overall_feedback = ""

        assessment = create_assessment(
            submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
            options_selected,  criterion_feedback, overall_feedback,
            rubric, scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
        )

        # The self-assessment should have set the feedback for
        # all criteria to an empty string.
        for part in assessment["parts"]:
            self.assertEqual(part["option"], None)
            self.assertEqual(
                part["feedback"], u'I thought it was about as accurate as Scrubs is to the medical profession.'
            )

    @patch('openassessment.assessment.api.self._complete_assessment')
    def test_create_assessment_database_error(self, mock_complete_assessment):
        mock_complete_assessment.side_effect = DatabaseError

        # Create a submission to self-assess
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        with self.assertRaises(SelfAssessmentInternalError):
            # Create a self-assessment for the submission
            assessment = create_assessment(
                submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
                self.OPTIONS_SELECTED, self.CRITERION_FEEDBACK, self.OVERALL_FEEDBACK, self.RUBRIC,
                scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
            )
