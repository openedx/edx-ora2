# coding=utf-8
import copy
import mock

from django.db import DatabaseError
from django.test.utils import override_settings
from ddt import ddt, data, file_data, unpack
from nose.tools import raises

from .constants import OPTIONS_SELECTED_DICT, RUBRIC, RUBRIC_OPTIONS, RUBRIC_POSSIBLE_POINTS, STUDENT_ITEM
from openassessment.assessment.test.test_ai import (
    ALGORITHM_ID,
    AI_ALGORITHMS,
    AIGradingTest,
    train_classifiers
)
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.api import staff as staff_api, ai as ai_api, peer as peer_api
from openassessment.assessment.api.self import create_assessment as self_assess
from openassessment.assessment.api.peer import create_assessment as peer_assess
from openassessment.assessment.models import Assessment, PeerWorkflow
from openassessment.assessment.errors import StaffAssessmentRequestError, StaffAssessmentInternalError
from openassessment.workflow import api as workflow_api
from submissions import api as sub_api


@ddt
class TestStaffAssessment(CacheResetTest):
    """
    Tests for staff assessments made as overrides, when none is required to exist.
    """

    STEP_REQUIREMENTS = {}
    STEP_REQUIREMENTS_WITH_STAFF = {'staff': {'required': True}}

    # This is due to ddt not playing nicely with list comprehensions
    ASSESSMENT_SCORES_DDT = [key for key in OPTIONS_SELECTED_DICT]

    @staticmethod
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def _ai_assess(sub):
        # Note that CLASSIFIER_SCORE_OVERRIDES matches OPTIONS_SELECTED_DICT['most'] scores
        train_classifiers(RUBRIC, AIGradingTest.CLASSIFIER_SCORE_OVERRIDES)
        ai_api.on_init(sub, rubric=RUBRIC, algorithm_id=ALGORITHM_ID)
        return ai_api.get_latest_assessment(sub)

    @staticmethod
    def _peer_assess(sub, scorer_id, scores):
        bob_sub, bob = TestStaffAssessment._create_student_and_submission("Bob", "Bob's answer", override_steps=['peer'])
        peer_api.get_submission_to_assess(bob_sub["uuid"], 1)
        return peer_assess(bob_sub["uuid"], bob["student_id"], scores, dict(), "", RUBRIC, 1)

    ASSESSMENT_TYPES_DDT = [
        ('self', lambda sub, scorer_id, scores: self_assess(sub, scorer_id, scores, dict(), "", RUBRIC)),
        ('peer', lambda sub, scorer_id, scores: TestStaffAssessment._peer_assess(sub, scorer_id, scores)),
        ('staff', lambda sub, scorer_id, scores: staff_api.create_assessment(sub, scorer_id, scores, dict(), "", RUBRIC)),
        ('ai', lambda sub, scorer_id, scores: TestStaffAssessment._ai_assess(sub))
    ]

    @data(*ASSESSMENT_SCORES_DDT)
    def test_create_assessment_not_required(self, key):
        """
        Simple test to ensure staff assessments are scored properly, for all values of OPTIONS_SELECTED_DICT,
        when staff scores are not required.
        """
        # Create assessment
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")

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

        #ensure submission is marked as finished
        # TODO: worflow finished?
        self.assertTrue(staff_api.assessment_is_finished(tim_sub["uuid"], self.STEP_REQUIREMENTS))

    @data(*ASSESSMENT_SCORES_DDT)
    def test_create_assessment_required(self, key):
        """
        Simple test to ensure staff assessments are scored properly, for all values of OPTIONS_SELECTED_DICT,
        when staff scores are required.
        """
        # Create assessment
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer", override_steps=['staff'])

        # Verify that we're still waiting on a staff assessment
        self.assertFalse(staff_api.assessment_is_finished(tim_sub["uuid"], self.STEP_REQUIREMENTS_WITH_STAFF))

        # Staff assess
        staff_assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            OPTIONS_SELECTED_DICT[key]["options"], dict(), "",
            RUBRIC,
        )

        # Verify assesment made, score updated, and no longer wating
        # TODO: worflow finished?
        self.assertEqual(staff_assessment["points_earned"], OPTIONS_SELECTED_DICT[key]["expected_points"])
        self.assertTrue(staff_api.assessment_is_finished(tim_sub["uuid"], self.STEP_REQUIREMENTS_WITH_STAFF))

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
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")

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
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer", override_steps=[initial_type])

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
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer", override_steps=[after_type])

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
        The idea behind this test:
            -the presence of a staff assessment makes a given submission "done"
            -exception: if this is an optional staff grade on top of a usually-requires-peer-assessment submission:
                -then the user must still peer grade the required number of responses before seeing their (staff-stermined) grade
        # TODO: better docstring once this is more thoroughly fleshed out
        """
        # Tim(student) makes a submission, for a problem that requires peer assessment
        tim_sub, tim = TestStaffAssessment._create_student_and_submission("Tim", "Tim's answer", override_steps=['peer'])
        # Bob(student) also makes a submission for that problem
        bob_sub, bob = TestStaffAssessment._create_student_and_submission("Bob", "Bob's answer", override_steps=['peer'])

        # Define peer requirements. Note that neither submission will fulfill must_be_graded_by
        requirements = {"peer": {"must_grade": 1, "must_be_graded_by": 2}}

        staff_score = "none"
        # Dumbledore(staff) uses override ability to provide a score for both submissions
        tim_assessment = staff_api.create_assessment(
            tim_sub["uuid"],
            "Dumbledore",
            OPTIONS_SELECTED_DICT[staff_score]["options"], dict(), "",
            RUBRIC,
        )
        bob_assessment = staff_api.create_assessment(
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

        # Verify that Tim's submission is not marked done, and he cannot get his score
        tim_workflow = workflow_api.get_workflow_for_submission(tim_sub["uuid"], requirements)
        self.assertEqual(tim_workflow["score"], None)

    def test_invalid_rubric_exception(self):
        # Create a submission
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")

        # Define invalid rubric
        invalid_rubric = copy.deepcopy(RUBRIC)
        for criterion in invalid_rubric["criteria"]:
            for option in criterion["options"]:
                option["points"] = -1

        # Try to staff assess with invalid rubric
        with self.assertRaises(StaffAssessmentRequestError) as context_manager:
            staff_assessment = staff_api.create_assessment(
                tim_sub["uuid"],
                "Dumbledore",
                OPTIONS_SELECTED_DICT["most"]["options"], dict(), "",
                invalid_rubric,
            )
        self.assertEqual(str(context_manager.exception), u"Rubric definition was not valid")

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
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")

        # Try to staff assess with invalid options selected
        with self.assertRaises(StaffAssessmentRequestError) as context_manager:
            staff_assessment = staff_api.create_assessment(
                tim_sub["uuid"],
                "Dumbledore",
                dict_to_use, dict(), "",
                RUBRIC,
            )
        self.assertEqual(str(context_manager.exception), u"Invalid options selected in the rubric")

    @mock.patch.object(Assessment.objects, 'filter')
    def test_database_filter_error_handling(self, mock_filter):
        # Create a submission
        tim_sub, tim = self._create_student_and_submission("Tim", "Tim's answer")

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
                OPTIONS_SELECTED_DICT['most']['options'], dict(), "",
                RUBRIC,
            )
        self.assertEqual(
            str(context_manager.exception),
            u"An error occurred while creating assessment by scorer with ID: {}".format("Dumbledore")
        )

    @staticmethod
    def _create_student_and_submission(student, answer, date=None, override_steps=None):
        """
        Helper method to create a student and submission for use in tests.
        """
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student
        submission = sub_api.create_submission(new_student_item, answer, date)
        steps = ['self']
        init_params = {}
        if override_steps:
            steps = override_steps
        if 'peer' in steps:
            peer_api.on_start(submission["uuid"])
        if 'ai' in steps:
            init_params['ai'] = {'rubric':RUBRIC, 'algorithm_id':ALGORITHM_ID}
        workflow_api.create_workflow(submission["uuid"], steps, init_params)
        return submission, new_student_item
