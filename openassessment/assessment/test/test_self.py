# -*- coding: utf-8 -*-
"""
Tests for self-assessment API.
"""

import copy
import datetime
import pytz
from openassessment.test_utils import CacheResetTest
from submissions.api import create_submission
from openassessment.assessment.api.self import (
    create_assessment, submitter_is_finished, get_assessment
)
from openassessment.assessment.errors import SelfAssessmentRequestError


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
            self.OPTIONS_SELECTED, self.RUBRIC,
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
        self.assertEqual(assessment['feedback'], u'')
        self.assertEqual(assessment['score_type'], u'SE')

    def test_create_assessment_no_submission(self):
        # Attempt to create a self-assessment for a submission that doesn't exist
        with self.assertRaises(SelfAssessmentRequestError):
            create_assessment(
                'invalid_submission_uuid', u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
                self.OPTIONS_SELECTED, self.RUBRIC,
                scored_at=datetime.datetime(2014, 4, 1).replace(tzinfo=pytz.utc)
            )

    def test_create_assessment_wrong_user(self):
        # Create a submission
        submission = create_submission(self.STUDENT_ITEM, "Test answer")

        # Attempt to create a self-assessment for the submission from a different user
        with self.assertRaises(SelfAssessmentRequestError):
            create_assessment(
                'invalid_submission_uuid', u'another user',
                self.OPTIONS_SELECTED, self.RUBRIC,
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
                options, self.RUBRIC,
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
                options, self.RUBRIC,
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
                options, self.RUBRIC,
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
            self.OPTIONS_SELECTED, self.RUBRIC,
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
            self.OPTIONS_SELECTED, self.RUBRIC,
        )

        # Attempt to self-assess again, which should raise an exception
        with self.assertRaises(SelfAssessmentRequestError):
            create_assessment(
                submission['uuid'], u'𝖙𝖊𝖘𝖙 𝖚𝖘𝖊𝖗',
                self.OPTIONS_SELECTED, self.RUBRIC,
            )

        # Expect that we still have the original assessment
        retrieved = get_assessment(submission["uuid"])
        self.assertItemsEqual(assessment, retrieved)

    def test_is_complete_no_submission(self):
        # This submission uuid does not exist
        self.assertFalse(submitter_is_finished('abc1234', {}))
