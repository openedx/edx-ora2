# coding=utf-8
"""
Tests for the assessment Django models.
"""
import copy
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.serializers import rubric_from_dict
from openassessment.assessment.models import Assessment, AssessmentPart, InvalidRubricSelection
from .constants import RUBRIC


class AssessmentTest(CacheResetTest):
    """
    Tests for the `Assessment` and `AssessmentPart` models.
    """

    def test_create_with_feedback_only_criterion(self):
        rubric = self._rubric_with_one_feedback_only_criterion()
        assessment = Assessment.create(rubric, "Bob", "submission UUID", "PE")

        # Create assessment parts
        # We can't select an option for the last criterion, but we do
        # provide written feedback.
        selected = {
            u"vøȼȺƀᵾłȺɍɏ": u"𝓰𝓸𝓸𝓭",
            u"ﻭɼค๓๓คɼ": u"єχ¢єℓℓєηт",
        }
        feedback = {
            u"feedback": u"𝕿𝖍𝖎𝖘 𝖎𝖘 𝖘𝖔𝖒𝖊 𝖋𝖊𝖊𝖉𝖇𝖆𝖈𝖐."
        }
        AssessmentPart.create_from_option_names(
            assessment, selected, feedback=feedback
        )

        # Check the score (the feedback-only assessment should count for 0 points)
        self.assertEqual(assessment.points_earned, 3)
        self.assertEqual(assessment.points_possible, 4)

        # Check the feedback text
        feedback_only = AssessmentPart.objects.get(criterion__name="feedback")
        self.assertEqual(feedback_only.feedback, u"𝕿𝖍𝖎𝖘 𝖎𝖘 𝖘𝖔𝖒𝖊 𝖋𝖊𝖊𝖉𝖇𝖆𝖈𝖐.")

    def test_create_with_all_feedback_only_criteria(self):
        rubric = self._rubric_with_all_feedback_only_criteria()
        assessment = Assessment.create(rubric, "Bob", "submission UUID", "PE")

        # Create assessment parts, each of which are feedback-only (no points)
        selected = {}
        feedback = {
            u"vøȼȺƀᵾłȺɍɏ": u"𝓰𝓸𝓸𝓭",
            u"ﻭɼค๓๓คɼ": u"єχ¢єℓℓєηт",
        }
        AssessmentPart.create_from_option_names(
            assessment, selected, feedback=feedback
        )

        # Check the score (should be 0, since we haven't selected any points)
        self.assertEqual(assessment.points_earned, 0)
        self.assertEqual(assessment.points_possible, 0)

    def test_create_from_option_points_feedback_only_criterion(self):
        rubric = self._rubric_with_one_feedback_only_criterion()
        assessment = Assessment.create(rubric, "Bob", "submission UUID", "PE")

        # Create assessment parts by providing scores for options
        # but NO feedback.  This simulates how an example-based AI
        # assessment is created.
        selected = {
            u"vøȼȺƀᵾłȺɍɏ": 2,
            u"ﻭɼค๓๓คɼ": 1,
        }
        AssessmentPart.create_from_option_points(assessment, selected)

        # Check the score (the feedback-only assessment should count for 0 points)
        self.assertEqual(assessment.points_earned, 3)
        self.assertEqual(assessment.points_possible, 4)

        # Check the feedback text (should default to an empty string)
        feedback_only = AssessmentPart.objects.get(criterion__name="feedback")
        self.assertEqual(feedback_only.feedback, u"")

    def test_create_from_option_points_all_feedback_only_criteria(self):
        rubric = self._rubric_with_all_feedback_only_criteria()
        assessment = Assessment.create(rubric, "Bob", "submission UUID", "PE")

        # Since there are no criteria with options, and we're not
        # providing written feedback, pass in an empty selection.
        selected = {}
        AssessmentPart.create_from_option_points(assessment, selected)

        # Score should be zero, since none of the criteria have options
        self.assertEqual(assessment.points_earned, 0)
        self.assertEqual(assessment.points_possible, 0)

    def test_default_feedback_for_feedback_only_criterion(self):
        rubric = self._rubric_with_one_feedback_only_criterion()
        assessment = Assessment.create(rubric, "Bob", "submission UUID", "PE")

        # Create assessment parts, but do NOT provide any feedback
        # This simulates how non-peer assessments are created
        # Note that this is different from providing an empty feedback dict;
        # here, we're not providing the `feedback` kwarg at all.
        selected = {
            u"vøȼȺƀᵾłȺɍɏ": u"𝓰𝓸𝓸𝓭",
            u"ﻭɼค๓๓คɼ": u"єχ¢єℓℓєηт",
        }
        AssessmentPart.create_from_option_names(assessment, selected)

        # Check the score (the feedback-only assessment should count for 0 points)
        self.assertEqual(assessment.points_earned, 3)
        self.assertEqual(assessment.points_possible, 4)

        # Check the feedback text, which should default to an empty string
        feedback_only = AssessmentPart.objects.get(criterion__name="feedback")
        self.assertEqual(feedback_only.feedback, u"")

    def test_no_feedback_provided_for_feedback_only_criterion(self):
        rubric = self._rubric_with_one_feedback_only_criterion()
        assessment = Assessment.create(rubric, "Bob", "submission UUID", "PE")

        # Create assessment parts
        # Do NOT provide feedback for the feedback-only criterion
        selected = {
            u"vøȼȺƀᵾłȺɍɏ": u"𝓰𝓸𝓸𝓭",
            u"ﻭɼค๓๓คɼ": u"єχ¢єℓℓєηт",
        }
        feedback = {}

        # Expect an error when we try to create the assessment parts
        with self.assertRaises(InvalidRubricSelection):
            AssessmentPart.create_from_option_names(assessment, selected, feedback=feedback)

    def _rubric_with_one_feedback_only_criterion(self):
        """Create a rubric with one feedback-only criterion."""
        rubric_dict = copy.deepcopy(RUBRIC)
        rubric_dict['criteria'].append({
            "order_num": 2,
            "name": u"feedback",
            "prompt": u"only feedback, no points",
            "options": []
        })
        return rubric_from_dict(rubric_dict)

    def _rubric_with_all_feedback_only_criteria(self):
        """Create a rubric with all feedback-only criteria."""
        rubric_dict = copy.deepcopy(RUBRIC)
        for criterion in rubric_dict['criteria']:
            criterion['options'] = []
        return rubric_from_dict(rubric_dict)

