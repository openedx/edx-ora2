# coding=utf-8
"""
Tests for staff assessments.
"""
from __future__ import absolute_import

import copy
from datetime import timedelta, datetime

from ddt import data, ddt, unpack
import mock

from django.db import DatabaseError
from django.utils.timezone import now

from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import staff as staff_api
from openassessment.assessment.api.peer import create_assessment as peer_assess
from openassessment.assessment.api.self import create_assessment as self_assess
from openassessment.assessment.errors import StaffAssessmentInternalError, StaffAssessmentRequestError
from openassessment.assessment.models import Assessment, StaffWorkflow, TeamStaffWorkflow
from openassessment.test_utils import CacheResetTest
from openassessment.tests.factories import StaffWorkflowFactory, TeamStaffWorkflowFactory, AssessmentFactory
from openassessment.workflow import api as workflow_api
from submissions import api as sub_api

from .constants import OPTIONS_SELECTED_DICT, RUBRIC, RUBRIC_OPTIONS, RUBRIC_POSSIBLE_POINTS, STUDENT_ITEM


@ddt
class TestStaffAssessment(CacheResetTest):
    """
    Tests for staff assessments made as overrides, when none is required to exist.
    """

    STEP_REQUIREMENTS = {}
    STEP_REQUIREMENTS_WITH_STAFF = {'required': True}

    # This is due to ddt not playing nicely with list comprehensions
    ASSESSMENT_SCORES_DDT = [key for key in OPTIONS_SELECTED_DICT]

    @staticmethod
    def _peer_assess(scores):
        """
        Helper to fulfill peer assessment requirements.
        """
        bob_sub, bob = TestStaffAssessment._create_student_and_submission("Bob", "Bob's answer", problem_steps=['peer'])
        peer_api.get_submission_to_assess(bob_sub["uuid"], 1)
        return peer_assess(bob_sub["uuid"], bob["student_id"], scores, dict(), "", RUBRIC, 1)

    ASSESSMENT_TYPES_DDT = [
        ('self', lambda sub, scorer_id, scores: self_assess(sub, scorer_id, scores, dict(), "", RUBRIC)),
        ('peer', lambda sub, scorer_id, scores: TestStaffAssessment._peer_assess(scores)),
        (
            'staff',
            lambda sub, scorer_id, scores: staff_api.create_assessment(sub, scorer_id, scores, dict(), "", RUBRIC)
        ),
    ]

    def _verify_done_state(self, uuid, requirements, expect_done=True):
        """
        Asserts that a submision and workflow are (or aren't) set to status "done".
        A False value for expect_done will confirm an assessment/workflow are NOT done.
        """
        workflow = workflow_api.get_workflow_for_submission(uuid, requirements)
        if expect_done:
            self.assertTrue(staff_api.assessment_is_finished(uuid, requirements))
            self.assertEqual(workflow["status"], "done")
        else:
            self.assertFalse(staff_api.assessment_is_finished(uuid, requirements))
            self.assertNotEqual(workflow["status"], "done")

    @data(*ASSESSMENT_SCORES_DDT)
    def test_create_assessment_not_required(self, key):
        """
        Simple test to ensure staff assessments are scored properly, for all values of OPTIONS_SELECTED_DICT,
        when staff scores are not required.
        """
        # Create assessment
        tim_sub, _ = self._create_student_and_submission("Tim", "Tim's answer")

        # Staff assess it
        assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            OPTIONS_SELECTED_DICT[key]["options"], dict(), "",
            RUBRIC,
        )

        # Ensure points are calculated properly
        self.assertEqual(assessment["points_earned"], OPTIONS_SELECTED_DICT[key]["expected_points"])
        self.assertEqual(assessment["points_possible"], RUBRIC_POSSIBLE_POINTS)

        # Ensure submission and workflow are marked as finished
        self._verify_done_state(tim_sub["uuid"], self.STEP_REQUIREMENTS)

    @data(*ASSESSMENT_SCORES_DDT)
    def test_create_assessment_required(self, key):
        """
        Simple test to ensure staff assessments are scored properly, for all values of OPTIONS_SELECTED_DICT,
        when staff scores are required.
        """
        # Create assessment
        tim_sub, _ = self._create_student_and_submission("Tim", "Tim's answer", problem_steps=['staff'])

        # Verify that we're still waiting on a staff assessment
        self._verify_done_state(tim_sub["uuid"], self.STEP_REQUIREMENTS_WITH_STAFF, expect_done=False)

        # Verify that a StaffWorkflow step has been created and is not complete
        workflow = StaffWorkflow.objects.get(submission_uuid=tim_sub['uuid'])
        self.assertIsNone(workflow.grading_completed_at)

        # Staff assess
        staff_assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            OPTIONS_SELECTED_DICT[key]["options"], dict(), "",
            RUBRIC,
        )

        # Verify assesment made, score updated, and no longer waiting
        self.assertEqual(staff_assessment["points_earned"], OPTIONS_SELECTED_DICT[key]["expected_points"])
        self._verify_done_state(tim_sub["uuid"], self.STEP_REQUIREMENTS_WITH_STAFF)
        # Verify that a StaffWorkflow step has been marked as complete
        workflow.refresh_from_db()
        self.assertIsNotNone(workflow.grading_completed_at)

    @data(*ASSESSMENT_SCORES_DDT)
    def test_create_assessment_score_overrides(self, key):
        """
        Test to ensure that scores can be overriden by a staff assessment using any value.
        """
        # Initially, self-asses with an all value
        initial_assessment = OPTIONS_SELECTED_DICT["all"]

        # Unless we're trying to override with an all value, then start with none
        if key == "all":
            initial_assessment = OPTIONS_SELECTED_DICT["none"]

        # Create assessment
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer", problem_steps=['self'])

        # Self assess it
        self_assessment = self_assess(
            tim_sub["uuid"],
            tim["student_id"],
            initial_assessment["options"], dict(), "",
            RUBRIC,
        )

        # Verify both assessment and workflow report correct score
        self.assertEqual(self_assessment["points_earned"], initial_assessment["expected_points"])
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], self.STEP_REQUIREMENTS)
        self.assertEqual(workflow["score"]["points_earned"], initial_assessment["expected_points"])

        # Now override with a staff assessment
        staff_assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            OPTIONS_SELECTED_DICT[key]["options"], dict(), "",
            RUBRIC,
        )

        # Verify both assessment and workflow report correct score
        self.assertEqual(staff_assessment["points_earned"], OPTIONS_SELECTED_DICT[key]["expected_points"])
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], self.STEP_REQUIREMENTS)
        self.assertEqual(workflow["score"]["points_earned"], OPTIONS_SELECTED_DICT[key]["expected_points"])

    @data(*ASSESSMENT_TYPES_DDT)
    @unpack
    def test_create_assessment_type_overrides(self, initial_type, initial_assess):
        """
        Test to ensure that any assesment, even a staff assessment, can be overriden by a staff assessment.
        """
        # Initially, asses with a 'most' value
        # This was selected to match the value that the ai test will set
        initial_assessment = OPTIONS_SELECTED_DICT["most"]

        # Create assessment
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer", problem_steps=[initial_type])

        # Initially assess it
        assessment = initial_assess(tim_sub["uuid"], tim["student_id"], initial_assessment["options"])
        # and update workflow with new scores
        requirements = self.STEP_REQUIREMENTS
        if initial_type == 'peer':
            requirements = {"peer": {"must_grade": 0, "must_be_graded_by": 1}}

        # Verify both assessment and workflow report correct score
        self.assertEqual(assessment["points_earned"], initial_assessment["expected_points"])
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], requirements)
        self.assertEqual(workflow["score"]["points_earned"], initial_assessment["expected_points"])

        staff_score = "few"
        # Now override with a staff assessment
        staff_assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            OPTIONS_SELECTED_DICT[staff_score]["options"], dict(), "",
            RUBRIC,
        )

        # Verify both assessment and workflow report correct score
        self.assertEqual(staff_assessment["points_earned"], OPTIONS_SELECTED_DICT[staff_score]["expected_points"])
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], requirements)
        self.assertEqual(workflow["score"]["points_earned"], OPTIONS_SELECTED_DICT[staff_score]["expected_points"])

    @data(*ASSESSMENT_TYPES_DDT)
    @unpack
    def test_create_assessment_does_not_block(self, after_type, after_assess):
        """
        Test to ensure that the presence of an override staff assessment only prevents new scores from being recorded;
        other assessments can still be made.
        """
        # Staff assessments do not block other staff scores from overriding, so skip that test
        if after_type == 'staff':
            return

        requirements = self.STEP_REQUIREMENTS
        if after_type == 'peer':
            requirements = {"peer": {"must_grade": 0, "must_be_graded_by": 1}}

        # Create assessment
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer", problem_steps=[after_type])

        staff_score = "few"
        # Staff assess it
        staff_assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            OPTIONS_SELECTED_DICT[staff_score]['options'], dict(), "",
            RUBRIC,
        )

        # Verify both assessment and workflow report correct score
        self.assertEqual(staff_assessment["points_earned"], OPTIONS_SELECTED_DICT[staff_score]["expected_points"])
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], requirements)
        # It's impossible to fake self requirements being complete, so we can't get the score for the self after_type
        if after_type != 'self':
            self.assertEqual(workflow["score"]["points_earned"], OPTIONS_SELECTED_DICT[staff_score]["expected_points"])

        # Now, non-force asses with a 'most' value
        # This was selected to match the value that the ai test will set
        unscored_assessment = OPTIONS_SELECTED_DICT["most"]
        assessment = after_assess(tim_sub["uuid"], tim["student_id"], unscored_assessment["options"])

        # Verify both assessment and workflow report correct score (workflow should report previous value)
        self.assertEqual(assessment["points_earned"], unscored_assessment["expected_points"])
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], requirements)
        self.assertEqual(workflow["score"]["points_earned"], OPTIONS_SELECTED_DICT[staff_score]["expected_points"])

    def test_provisionally_done(self):
        """
        Test to ensure that blocking steps, such as peer, are not considered done and do not display a score
        if the submitter's requirements have not yet been met, even if a staff score has been recorded.

        This test also ensures that a user may submit peer assessments after having been staff assessed, which was
        a bug that had been previously present.
        """
        # Tim(student) makes a submission, for a problem that requires peer assessment
        tim_sub, _ = TestStaffAssessment._create_student_and_submission("Tim", "Tim's answer", problem_steps=['peer'])
        # Bob(student) also makes a submission for that problem
        bob_sub, bob = TestStaffAssessment._create_student_and_submission("Bob", "Bob's answer", problem_steps=['peer'])

        # Define peer requirements. Note that neither submission will fulfill must_be_graded_by
        requirements = {"peer": {"must_grade": 1, "must_be_graded_by": 2}}

        staff_score = "none"
        # Dumbledore(staff) uses override ability to provide a score for both submissions
        staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            OPTIONS_SELECTED_DICT[staff_score]["options"], dict(), "",
            RUBRIC,
        )
        staff_api.create_assessment(
            bob_sub["uuid"],
            "Dumbledore",
            OPTIONS_SELECTED_DICT[staff_score]["options"], dict(), "",
            RUBRIC,
        )

        # Bob completes his peer assessment duties, Tim does not
        peer_api.get_submission_to_assess(bob_sub["uuid"], 1)
        peer_assess(
            bob_sub["uuid"],
            bob["student_id"],
            OPTIONS_SELECTED_DICT["most"]["options"], dict(), "",
            RUBRIC,
            requirements["peer"]["must_be_graded_by"]
        )

        # Verify that Bob's submission is marked done and returns the proper score
        bob_workflow = workflow_api.get_workflow_for_submission(bob_sub["uuid"], requirements)
        self.assertEqual(bob_workflow["score"]["points_earned"], OPTIONS_SELECTED_DICT[staff_score]["expected_points"])
        self.assertEqual(bob_workflow["status"], "done")

        # Verify that Tim's submission is not marked done, and he cannot get his score
        tim_workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], requirements)
        self.assertEqual(tim_workflow["score"], None)
        self.assertNotEqual(tim_workflow["status"], "done")

    def test_update_with_override(self):
        """
        Test that, when viewing a submission with a staff override present, the workflow is not updated repeatedly.

        See TNL-6092 for some historical context.
        """
        tim_sub, _ = TestStaffAssessment._create_student_and_submission("Tim", "Tim's answer", problem_steps=['self'])
        staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            OPTIONS_SELECTED_DICT["none"]["options"], dict(), "",
            RUBRIC,
        )
        workflow_api.get_workflow_for_submission(tim_sub["uuid"], {})
        with mock.patch('openassessment.workflow.models.sub_api.reset_score') as mock_reset:
            workflow_api.get_workflow_for_submission(tim_sub["uuid"], {})
            self.assertFalse(mock_reset.called)

    def test_invalid_rubric_exception(self):
        # Create a submission
        tim_sub, _ = self._create_student_and_submission("Tim", "Tim's answer")

        # Define invalid rubric
        invalid_rubric = copy.deepcopy(RUBRIC)
        for criterion in invalid_rubric["criteria"]:
            for option in criterion["options"]:
                option["points"] = -1

        # Try to staff assess with invalid rubric
        with self.assertRaises(StaffAssessmentRequestError) as context_manager:
            staff_api.create_assessment(
                tim_sub["uuid"],
                "Dumbledore",
                OPTIONS_SELECTED_DICT["most"]["options"], dict(), "",
                invalid_rubric,
            )
        self.assertEqual(str(context_manager.exception), u"The rubric definition is not valid.")

    @data("criterion_not_found", "option_not_found", "missing_criteria", "some_criteria_not_assessed")
    def test_invalid_rubric_options_exception(self, invalid_reason):
        # Define invalid options_selected
        dict_to_use = copy.deepcopy(OPTIONS_SELECTED_DICT['all']["options"])
        if invalid_reason == "criterion_not_found":
            dict_to_use["invalid"] = RUBRIC_OPTIONS[0]["name"]
        elif invalid_reason == "option_not_found":
            dict_to_use[RUBRIC["criteria"][0]["name"]] = "invalid"
        elif invalid_reason == "missing_criteria":
            del dict_to_use[RUBRIC["criteria"][0]["name"]]
        elif invalid_reason == "some_criteria_not_assessed":
            dict_to_use[RUBRIC["criteria"][0]["name"]] = None

        # Create a submission
        tim_sub, _ = self._create_student_and_submission("Tim", "Tim's answer")

        # Try to staff assess with invalid options selected
        with self.assertRaises(StaffAssessmentRequestError) as context_manager:
            staff_api.create_assessment(
                tim_sub["uuid"],
                "Dumbledore",
                dict_to_use, dict(), "",
                RUBRIC,
            )
        self.assertEqual(str(context_manager.exception), u"Invalid options were selected in the rubric.")

    @mock.patch('openassessment.assessment.models.Assessment.objects.filter')
    def test_database_filter_error_handling(self, mock_filter):
        # Create a submission
        mock_filter.return_value = Assessment.objects.none()
        tim_sub, _ = self._create_student_and_submission("Tim", "Tim's answer")

        # Note that we have to define this side effect *after* creating the submission
        mock_filter.side_effect = DatabaseError("KABOOM!")

        # Try to get the latest staff assessment, handle database errors
        with self.assertRaises(StaffAssessmentInternalError) as context_manager:
            staff_api.get_latest_staff_assessment(tim_sub["uuid"])
        self.assertEqual(
            str(context_manager.exception),
            (
                u"An error occurred while retrieving staff assessments for the submission with UUID {uuid}: {ex}"
            ).format(uuid=tim_sub["uuid"], ex="KABOOM!")
        )

        # Try to get staff assessment scores by criteria, handle database errors
        with self.assertRaises(StaffAssessmentInternalError) as context_manager:
            staff_api.get_assessment_scores_by_criteria(tim_sub["uuid"])
        self.assertEqual(
            str(context_manager.exception),
            u"Error getting staff assessment scores for {}".format(tim_sub["uuid"])
        )

    @mock.patch('openassessment.assessment.models.Assessment.create')
    def test_database_create_error_handling(self, mock_create):
        mock_create.side_effect = DatabaseError("KABOOM!")

        # Try to create a staff assessment, handle database errors
        with self.assertRaises(StaffAssessmentInternalError) as context_manager:
            staff_api.create_assessment(
                "000000",
                "Dumbledore",
                OPTIONS_SELECTED_DICT['most']['options'], dict(), "",
                RUBRIC,
            )
        self.assertEqual(
            str(context_manager.exception),
            u"An error occurred while creating an assessment by the scorer with this ID: {}".format("Dumbledore")
        )

    def test_fetch_next_submission(self):
        bob_sub, _ = self._create_student_and_submission("bob", "bob's answer")
        _, tim = self._create_student_and_submission("Tim", "Tim's answer")
        submission = staff_api.get_submission_to_assess(tim['course_id'], tim['item_id'], tim['student_id'])
        self.assertIsNotNone(submission)
        self.assertEqual(bob_sub, submission)

    def test_fetch_same_submission(self):
        bob_sub, bob = self._create_student_and_submission("bob", "bob's answer")
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")
        tim_to_grade = staff_api.get_submission_to_assess(tim['course_id'], tim['item_id'], tim['student_id'])
        self.assertEqual(bob_sub, tim_to_grade)
        # Ensure that Bob doesn't pick up the submission that Tim is grading.
        bob_to_grade = staff_api.get_submission_to_assess(tim['course_id'], tim['item_id'], bob['student_id'])
        tim_to_grade = staff_api.get_submission_to_assess(tim['course_id'], tim['item_id'], tim['student_id'])
        self.assertEqual(bob_sub, tim_to_grade)
        self.assertEqual(tim_sub, bob_to_grade)

    def test_fetch_submission_delayed(self):
        bob_sub, bob = self._create_student_and_submission("bob", "bob's answer")
        # Fetch the submission for Tim to grade
        tim_to_grade = staff_api.get_submission_to_assess(bob['course_id'], bob['item_id'], "Tim")
        self.assertEqual(bob_sub, tim_to_grade)

        bob_to_grade = staff_api.get_submission_to_assess(bob['course_id'], bob['item_id'], bob['student_id'])
        self.assertIsNone(bob_to_grade)

        # Change the grading_started_at timestamp so that the 'lock' on the
        # problem is released.
        workflow = StaffWorkflow.objects.get(scorer_id="Tim")
        # pylint: disable=unicode-format-string
        timestamp = (now() - (workflow.TIME_LIMIT + timedelta(hours=1))).strftime("%Y-%m-%d %H:%M:%S")
        workflow.grading_started_at = timestamp
        workflow.save()

        bob_to_grade = staff_api.get_submission_to_assess(bob['course_id'], bob['item_id'], bob['student_id'])
        self.assertEqual(tim_to_grade, bob_to_grade)

    def test_next_submission_error(self):
        _, tim = self._create_student_and_submission("Tim", "Tim's answer")
        with mock.patch('openassessment.assessment.api.staff.submissions_api.get_submission') as patched_get_submission:
            patched_get_submission.side_effect = sub_api.SubmissionNotFoundError('Failed')
            with self.assertRaises(staff_api.StaffAssessmentInternalError):
                staff_api.get_submission_to_assess(tim['course_id'], tim['item_id'], tim['student_id'])

    def test_no_available_submissions(self):
        _, tim = self._create_student_and_submission("Tim", "Tim's answer")
        # Use a non-existent course and non-existent item.
        submission = staff_api.get_submission_to_assess('test_course_id', 'test_item_id', tim['student_id'])
        self.assertIsNone(submission)

    def test_cancel_staff_workflow(self):
        tim_sub, _ = self._create_student_and_submission("Tim", "Tim's answer")
        workflow_api.cancel_workflow(tim_sub['uuid'], "Test Cancel", "Bob", {})
        workflow = StaffWorkflow.objects.get(submission_uuid=tim_sub['uuid'])
        self.assertTrue(workflow.is_cancelled)

    def test_grading_statistics(self):
        _, bob = self._create_student_and_submission("bob", "bob's answer")
        course_id = bob['course_id']
        item_id = bob['item_id']
        _, tim = self._create_student_and_submission("Tim", "Tim's answer")
        self._create_student_and_submission("Sue", "Sue's answer")
        stats = staff_api.get_staff_grading_statistics(course_id, item_id)
        self.assertEqual(stats, {'graded': 0, 'ungraded': 3, 'in-progress': 0})

        # Fetch a grade so that there's one 'in-progress'
        tim_to_grade = staff_api.get_submission_to_assess(course_id, item_id, tim['student_id'])
        stats = staff_api.get_staff_grading_statistics(course_id, item_id)
        self.assertEqual(stats, {'graded': 0, 'ungraded': 2, 'in-progress': 1})

        bob_to_grade = staff_api.get_submission_to_assess(tim['course_id'], tim['item_id'], bob['student_id'])
        stats = staff_api.get_staff_grading_statistics(course_id, item_id)
        self.assertEqual(stats, {'graded': 0, 'ungraded': 1, 'in-progress': 2})

        # Grade one of the submissions
        staff_api.create_assessment(
            tim_to_grade["uuid"],
            tim['student_id'],
            OPTIONS_SELECTED_DICT["all"]["options"], dict(), "",
            RUBRIC,
        )
        stats = staff_api.get_staff_grading_statistics(course_id, item_id)
        self.assertEqual(stats, {'graded': 1, 'ungraded': 1, 'in-progress': 1})

        # When one of the 'locks' times out, verify that it is no longer
        # considered ungraded.
        workflow = StaffWorkflow.objects.get(scorer_id=bob['student_id'])
        # pylint: disable=unicode-format-string
        timestamp = (now() - (workflow.TIME_LIMIT + timedelta(hours=1))).strftime("%Y-%m-%d %H:%M:%S")
        workflow.grading_started_at = timestamp
        workflow.save()
        stats = staff_api.get_staff_grading_statistics(course_id, item_id)
        self.assertEqual(stats, {'graded': 1, 'ungraded': 2, 'in-progress': 0})

        workflow_api.cancel_workflow(bob_to_grade['uuid'], "Test Cancel", bob['student_id'], {})
        stats = staff_api.get_staff_grading_statistics(course_id, item_id)
        self.assertEqual(stats, {'graded': 1, 'ungraded': 1, 'in-progress': 0})

    @staticmethod
    def _create_student_and_submission(student, answer, date=None, problem_steps=None):
        """
        Helper method to create a student and submission for use in tests.
        """
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        submission = sub_api.create_submission(new_student_item, answer, date)
        steps = []
        init_params = {}
        if problem_steps:
            steps = problem_steps
        if 'peer' in steps:
            peer_api.on_start(submission["uuid"])
        workflow_api.create_workflow(submission["uuid"], steps, init_params)
        return submission, new_student_item


@ddt
class BaseStaffWorkflowModelTestMixin(object):
    item_id = 'itemitemitemimitem'
    other_item_id = 'other_item_id'
    course_id = 'edx/TestCourse/CourseRun2'
    other_course_id = 'edx/SomeOtherCourse/CourseRun15'
    scorer_1_id = 'scorer1'
    scorer_2_id = 'scorer2'

    @classmethod
    def setUpTestData(cls):
        """
        Make some graded, ungraded and in-progress workflows for another item in this
        course and in another course, just for some noise
        """
        for _ in range(2):
            cls._create_in_progress(
                course_id=cls.other_course_id,
                item_id=cls.other_item_id,
                scorer_id=cls.scorer_2_id)
            cls._create_ungraded(course_id=cls.other_course_id, item_id=cls.other_item_id)
            cls._create_graded(course_id=cls.other_course_id, item_id=cls.other_item_id, scorer_id=cls.scorer_1_id)

            cls._create_in_progress(item_id=cls.other_item_id, scorer_id=cls.scorer_2_id)
            cls._create_ungraded(item_id=cls.other_item_id)
            cls._create_graded(item_id=cls.other_item_id, scorer_id=cls.scorer_1_id)

    @classmethod
    def _create_in_progress(cls, course_id=None, item_id=None, scorer_id=''):
        """
        """
        # pylint: disable=unexpected-keyword-arg
        return cls.create_workflow(
            course_id=course_id or cls.course_id,
            item_id=item_id or cls.item_id,
            scorer_id=scorer_id,
            grading_completed_at=None,
            cancelled_at=None,
            grading_started_at=datetime.now(),
        )

    @classmethod
    def _create_ungraded(cls, course_id=None, item_id=None, scorer_id='', grading_started_at=None):
        """
        Create an ungraded workflow with the given fields.

        A workflow can still be ungraded if it has a scorer_id and grading_started_at,
        as long as grading_started_at is before the timeout. This function doesn't actually do
        that validation, beware.
        """
        # pylint: disable=unexpected-keyword-arg
        return cls.create_workflow(
            course_id=course_id or cls.course_id,
            item_id=item_id or cls.item_id,
            grading_completed_at=None,
            cancelled_at=None,
            scorer_id=scorer_id,
            grading_started_at=grading_started_at,
        )

    @classmethod
    def _create_graded(cls, course_id=None, item_id=None, scorer_id=''):
        """
        """
        # pylint: disable=unexpected-keyword-arg
        return cls.create_workflow(
            course_id=course_id or cls.course_id,
            item_id=item_id or cls.item_id,
            scorer_id=scorer_id,
            cancelled_at=None,
            grading_completed_at=datetime.now()
        )

    def test_cancelled(self):
        workflow = self.create_workflow()
        self.assertFalse(workflow.is_cancelled)
        workflow.cancelled_at = datetime.now()
        self.assertTrue(workflow.is_cancelled)

    @unpack
    @data(
        (0, 5, 7),
        (3, 0, 4),
        (5, 2, 0),
        (0, 0, 0),
    )
    def test_get_workflow_statistics(self, expected_graded, expected_ungraded, expected_in_progress):
        for _ in range(expected_graded):
            self._create_graded()
        for _ in range(expected_ungraded):
            self._create_ungraded()
        for _ in range(expected_in_progress):
            self._create_in_progress()
        stats = self.model.get_workflow_statistics(self.course_id, self.item_id)
        self.assertDictEqual(
            {
                'graded': expected_graded,
                'ungraded': expected_ungraded,
                'in-progress': expected_in_progress,
            },
            stats
        )

    def _get_and_assert_workflow(self, expected_workflow):
        submission_uuid = self.model.get_submission_for_review(self.course_id, self.item_id, self.scorer_1_id)
        selected_workflow = self.get_workflow_by_identifying_uuid(submission_uuid)

        # Check that the workflow is the workflow we expect, and that scorer_id was updated, and that
        # grading_started_at was set no more than a second ago.
        self.assertEqual(expected_workflow.id, selected_workflow.id)
        self.assertEqual(self.scorer_1_id, selected_workflow.scorer_id)

        now = datetime.now(tz=selected_workflow.grading_started_at.tzinfo)
        timediff = now - selected_workflow.grading_started_at
        self.assertTrue(timediff < timedelta(seconds=1))

    def test_get_submission_for_review_previously_graded(self):
        """
        When getting a submission to review, prioritize submissions
        that the reviewer has previously worked on
        """
        #Create three ungraded
        self._create_ungraded()
        self._create_ungraded()
        self._create_ungraded()

        #Create graded and in-progress for graders 1 and 2
        self._create_graded(scorer_id=self.scorer_1_id)
        in_progress_scorer_1 = self._create_in_progress(scorer_id=self.scorer_1_id)

        self._create_graded(scorer_id=self.scorer_2_id)
        self._create_in_progress(scorer_id=self.scorer_2_id)

        self._get_and_assert_workflow(in_progress_scorer_1)


    def test_get_submission_for_review_no_scorer(self):
        """
        When getting a submission to review, if there are no workflows the 
        reviewer has worked on, get one that has no scorer (or has timed out)
        """
        self._create_graded(scorer_id=self.scorer_1_id)
        self._create_in_progress(scorer_id=self.scorer_2_id)
        no_scorer = self._create_ungraded()

        self._get_and_assert_workflow(no_scorer)


    def test_get_submission_for_review_in_progress_past_timeout(self):
        """
        When getting a submission to review, if there are no workflows the 
        reviewer has worked on, get one that has timed out (or has no scorer)
        """
        self._create_graded(scorer_id=self.scorer_1_id)
        self._create_in_progress(scorer_id=self.scorer_2_id)
        
        hour_past_time_limit_td = self.model.TIME_LIMIT + timedelta(hours=1)
        grading_start = datetime.now() - hour_past_time_limit_td
        timed_out = self._create_ungraded(scorer_id=self.scorer_2_id, grading_started_at=grading_start)

        self._get_and_assert_workflow(timed_out)

    def test_get_submission_for_review_no_available(self):
        self._create_graded(scorer_id=self.scorer_1_id)
        self._create_graded(scorer_id=self.scorer_2_id)
        self._create_in_progress(scorer_id=self.scorer_2_id)

        submission_uuid = self.model.get_submission_for_review(self.course_id, self.item_id, self.scorer_1_id)
        self.assertIsNone(submission_uuid)

    def test_database_error(self):
        self._create_ungraded()
        with mock.patch.object(self.model, 'save') as mocked_save:
            mocked_save.side_effect = DatabaseError
            with self.assertRaises(StaffAssessmentInternalError):
                self.model.get_submission_for_review(self.course_id, self.item_id, self.scorer_1_id)

    def test_close_active_assessment(self):
        workflow = self.create_workflow()
        self.assertIsNone(workflow.assessment)
        self.assertEqual('', workflow.scorer_id)
        self.assertIsNone(workflow.grading_completed_at)

        assessment = AssessmentFactory.create()
        workflow.close_active_assessment(assessment, self.scorer_1_id)

        self.assertEqual(assessment.id, workflow.assessment)
        self.assertEqual(self.scorer_1_id, workflow.scorer_id)
        self.assertIsNotNone(workflow.grading_completed_at)


class StaffWorkflowModelTest(BaseStaffWorkflowModelTestMixin, CacheResetTest):

    model = StaffWorkflow

    @classmethod
    def create_workflow(cls, **kwargs):
        return StaffWorkflowFactory.create(**kwargs)

    def get_workflow_by_identifying_uuid(self, uuid):
        return StaffWorkflow.objects.get(submission_uuid=uuid)

    def test_identifying_uuid(self):
        workflow = self.create_workflow()
        self.assertEqual(workflow.submission_uuid, workflow.identifying_uuid)


class TeamStaffWorkflowModelTest(BaseStaffWorkflowModelTestMixin, CacheResetTest):

    model = TeamStaffWorkflow

    @classmethod
    def create_workflow(cls, **kwargs):
        return TeamStaffWorkflowFactory.create(**kwargs)

    def get_workflow_by_identifying_uuid(self, uuid):
        return TeamStaffWorkflow.objects.get(team_submission_uuid=uuid)

    def test_identifying_uuid(self):
        workflow = self.create_workflow()
        self.assertNotEqual(workflow.submission_uuid, workflow.identifying_uuid)
        self.assertEqual(workflow.team_submission_uuid, workflow.identifying_uuid)
