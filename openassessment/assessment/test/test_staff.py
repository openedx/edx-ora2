# coding=utf-8
import copy
import mock

from django.db import DatabaseError
from ddt import ddt, file_data
from nose.tools import raises

from openassessment.test_utils import CacheResetTest
from openassessment.assessment.api import staff as staff_api
from openassessment.assessment.api.self import create_assessment as self_assess
from openassessment.assessment.models import Assessment
from openassessment.assessment.errors import StaffAssessmentRequestError, StaffAssessmentInternalError
from openassessment.workflow import api as workflow_api
from submissions import api as sub_api

STUDENT_ITEM = dict(
    student_id="Tim",
    course_id="Demo_Course",
    item_id="item_one",
    item_type="Peer_Submission",
)

# Possible points: 14
RUBRIC_DICT = {
    "criteria": [
        {
            "name": "secret",
            "prompt": "Did the writer keep it secret?",
            "options": [
                {"name": "no", "points": "0", "explanation": ""},
                {"name": "yes", "points": "1", "explanation": ""},
            ]
        },
        {
            "name": u"ⓢⓐⓕⓔ",
            "prompt": "Did the writer keep it safe?",
            "options": [
                {"name": "no", "points": "0", "explanation": ""},
                {"name": "yes", "points": "1", "explanation": ""},
            ]
        },
        {
            "name": "giveup",
            "prompt": "How willing is the writer to give up the ring?",
            "options": [
                {
                    "name": "unwilling",
                    "points": "0",
                    "explanation": "Likely to use force to keep it."
                },
                {
                    "name": "reluctant",
                    "points": "3",
                    "explanation": "May argue, but will give it up voluntarily."
                },
                {
                    "name": "eager",
                    "points": "10",
                    "explanation": "Happy to give it up."
                }
            ]
        },
        {
            "name": "singing",
            "prompt": "Did the writer break into tedious elvish lyrics?",
            "options": [
                {"name": "no", "points": "2", "explanation": ""},
                {"name": "yes", "points": "0", "explanation": ""}
            ]
        },
    ]
}

# Answers are against RUBRIC_DICT -- this is worth 6 points
ASSESSMENT_DICT = {
    'overall_feedback': u"这是中国",
    'criterion_feedback': {
        "giveup": u"𝓨𝓸𝓾 𝓼𝓱𝓸𝓾𝓵𝓭𝓷'𝓽 𝓰𝓲𝓿𝓮 𝓾𝓹!"
    },
    'options_selected': {
        "secret": "yes",
        u"ⓢⓐⓕⓔ": "no",
        "giveup": "reluctant",
        "singing": "no",
    },
}

# Answers are against RUBRIC_DICT -- this is worth 14 points
ASSESSMENT_DICT_PASS = {
    'overall_feedback': u"这是中国",
    'criterion_feedback': {},
    'options_selected': {
        "secret": "yes",
        u"ⓢⓐⓕⓔ": "yes",
        "giveup": "eager",
        "singing": "no",
    }
}

@ddt
class TestStaffOverwrite(CacheResetTest):
    """
    Tests for staff assessments made as overrides, when none is required to exist.
    """

    STEPS = ['self']
    STEP_REQUIREMENTS = {}
    STEP_REQUIREMENTS_WITH_STAFF = {'staff': {'required': True}}

    def test_create_assessment_points(self):
        # Create assessment
        tim_sub, tim = self.create_student_and_submission("Tim", "Tim's answer")

        # Staff assess it
        assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            ASSESSMENT_DICT['options_selected'], dict(), "",
            RUBRIC_DICT,
        )

        # Ensure points are calculated properly
        self.assertEqual(assessment["points_earned"], 6)
        self.assertEqual(assessment["points_possible"], 14)

        #ensure submission is marked as finished
        self.assertTrue(staff_api.assessment_is_finished(tim_sub["uuid"], self.STEP_REQUIREMENTS))

    def test_create_assessment_overrides(self):
        # Create assessment
        tim_sub, tim = self.create_student_and_submission("Tim", "Tim's answer")

        # Self assess it
        self_assessment = self_assess(
            tim_sub["uuid"],
            tim["student_id"],
            ASSESSMENT_DICT['options_selected'], dict(), "",
            RUBRIC_DICT,
        )
        # and update workflow with new scores
        workflow_api.update_from_assessments(tim_sub["uuid"], self.STEP_REQUIREMENTS)

        # Verify both assessment and workflow report correct score
        self.assertEqual(self_assessment["points_earned"], 6)
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], self.STEP_REQUIREMENTS)
        self.assertEqual(workflow["score"]["points_earned"], 6)

        # Now override with a staff assessment
        staff_assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            ASSESSMENT_DICT_PASS['options_selected'], dict(), "",
            RUBRIC_DICT,
        )
        # Be sure to update the workflow!
        workflow_api.update_from_assessments(tim_sub["uuid"], self.STEP_REQUIREMENTS, force_update_score=True)

        # Verify both assessment and workflow report correct score
        self.assertEqual(staff_assessment["points_earned"], 14)
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], self.STEP_REQUIREMENTS)
        self.assertEqual(workflow["score"]["points_earned"], 14)

    def test_create_assessment_does_not_block(self):
        # Create assessment
        tim_sub, tim = self.create_student_and_submission("Tim", "Tim's answer")

        # Staff assess it
        staff_assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            ASSESSMENT_DICT_PASS['options_selected'], dict(), "",
            RUBRIC_DICT,
        )
        # Keep the workflow updated
        workflow_api.update_from_assessments(tim_sub["uuid"], self.STEP_REQUIREMENTS, force_update_score=True)

        # Ensure points are what we expect
        self.assertEqual(staff_assessment["points_earned"], 14)
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], self.STEP_REQUIREMENTS)
        self.assertEqual(workflow["score"]["points_earned"], 14)

        # Now self assess, and ensure assessment is recorded
        self_assessment = self_assess(
            tim_sub["uuid"],
            tim["student_id"],
            ASSESSMENT_DICT['options_selected'], dict(), "",
            RUBRIC_DICT,
        )
        self.assertEqual(self_assessment["points_earned"], 6)

        # Ensure points are not updated
        workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], self.STEP_REQUIREMENTS)
        self.assertEqual(workflow["score"]["points_earned"], 14)

    def test_staff_assessment_required(self):
        # Set up submission, with staff as a required step on the workflow
        tim_sub, tim = self.create_student_and_submission("Tim", "Tim's answer", require_staff=True)

        # Verify that we're still waiting on a staff assessment
        self.assertFalse(staff_api.assessment_is_finished(tim_sub["uuid"], self.STEP_REQUIREMENTS_WITH_STAFF))

        # Staff assess, without using force_update parameter
        staff_assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            ASSESSMENT_DICT_PASS['options_selected'], dict(), "",
            RUBRIC_DICT,
        )
        workflow_api.update_from_assessments(tim_sub["uuid"], self.STEP_REQUIREMENTS_WITH_STAFF)

        # Verify assesment made, score updated, and no longer wating
        self.assertEqual(staff_assessment["points_earned"], 14)
        self.assertTrue(staff_api.assessment_is_finished(tim_sub["uuid"], self.STEP_REQUIREMENTS_WITH_STAFF))

    def test_invalid_rubric_exceptions(self):
        # Create a submission
        tim_sub, tim = self.create_student_and_submission("Tim", "Tim's answer")

        # Define invalid rubric and options_selected
        invalid_rubric = copy.deepcopy(RUBRIC_DICT)
        for criterion in invalid_rubric["criteria"]:
            for option in criterion["options"]:
                option["points"] = -1

        invalid_options_selected = {
            "secret": "meow",
            u"ⓢⓐⓕⓔ": "bark",
            "giveup": "moo",
            "singing": "oink",
        }

        # Try to staff assess with invalid rubric
        with self.assertRaises(StaffAssessmentRequestError) as context_manager:
            staff_assessment = staff_api.create_assessment(
                tim_sub["uuid"],
                "Dumbledore",
                ASSESSMENT_DICT_PASS['options_selected'], dict(), "",
                invalid_rubric,
            )
        self.assertEqual(str(context_manager.exception), u"Rubric definition was not valid")

        # Try to staff assess with invalid options selected
        with self.assertRaises(StaffAssessmentRequestError) as context_manager:
            staff_assessment = staff_api.create_assessment(
                tim_sub["uuid"],
                "Dumbledore",
                invalid_options_selected, dict(), "",
                RUBRIC_DICT,
            )
        self.assertEqual(str(context_manager.exception), u"Invalid options selected in the rubric")

    @mock.patch.object(Assessment.objects, 'filter')
    def test_database_filter_error_handling(self, mock_filter):
        # Create a submission
        tim_sub, tim = self.create_student_and_submission("Tim", "Tim's answer")

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

    @mock.patch.object(Assessment, 'create')
    def test_database_create_error_handling(self, mock_create):
        mock_create.side_effect = DatabaseError("KABOOM!")

        # Try to create a staff assessment, handle database errors
        with self.assertRaises(StaffAssessmentInternalError) as context_manager:
            staff_assessment = staff_api.create_assessment(
                "000000",
                "Dumbledore",
                ASSESSMENT_DICT_PASS['options_selected'], dict(), "",
                RUBRIC_DICT,
            )
        self.assertEqual(
            str(context_manager.exception),
            u"An error occurred while creating assessment by scorer with ID: {}".format("Dumbledore")
        )

    def create_student_and_submission(self, student, answer, date=None, require_staff=False):
        """
        Helper method to create a student and submission for use in tests.
        """
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        submission = sub_api.create_submission(new_student_item, answer, date)
        steps = self.STEPS
        if require_staff:
            steps.append('staff')
        workflow_api.create_workflow(submission["uuid"], steps)
        return submission, new_student_item
