# coding=utf-8
"""
Tests for assessment serializers.
"""

import copy
import json
import os.path

from openassessment.assessment.models import Assessment, AssessmentFeedback, AssessmentPart
from openassessment.assessment.serializers import (AssessmentFeedbackSerializer, InvalidRubric, full_assessment_dict,
                                                   rubric_from_dict)
from openassessment.test_utils import CacheResetTest

from .constants import RUBRIC


def json_data(filename):
    curr_dir = os.path.dirname(__file__)
    with open(os.path.join(curr_dir, filename), "rb") as json_file:
        return json.load(json_file)


class RubricDeserializationTest(CacheResetTest):

    def test_rubric_only_created_once(self):
        # Make sure sending the same Rubric data twice only creates one Rubric,
        # and returns a reference to it the next time.
        rubric_data = json_data('data/rubric/project_plan_rubric.json')

        r1 = rubric_from_dict(rubric_data)

        with self.assertNumQueries(1):
            # Just the select -- shouldn't need the create queries
            r2 = rubric_from_dict(rubric_data)

        self.assertEqual(r1.id, r2.id)
        r1.delete()

    def test_rubric_requires_positive_score(self):
        with self.assertRaises(InvalidRubric):
            rubric_from_dict(json_data('data/rubric/no_points.json'))


class CriterionDeserializationTest(CacheResetTest):

    def test_empty_criteria(self):
        with self.assertRaises(InvalidRubric) as cm:
            rubric_from_dict(json_data('data/rubric/empty_criteria.json'))
        self.assertEqual(
            cm.exception.errors,
            {'criteria': [u'Must have at least one criterion']}
        )

    def test_missing_criteria(self):
        with self.assertRaises(InvalidRubric) as cm:
            rubric_from_dict(json_data('data/rubric/missing_criteria.json'))
        self.assertEqual(
            cm.exception.errors,
            {'criteria': [u'This field is required.']}
        )


class CriterionOptionDeserializationTest(CacheResetTest):

    def test_empty_options(self):
        rubric = rubric_from_dict(json_data('data/rubric/empty_options.json'))
        self.assertEqual(rubric.criteria.count(), 2)

    def test_missing_options(self):
        with self.assertRaises(InvalidRubric) as cm:
            rubric_from_dict(json_data('data/rubric/missing_options.json'))
        self.assertEqual(
            cm.exception.errors,
            {
                'criteria': [
                    {'options': [u'This field is required.']},
                    {}  # No errors in second criterion
                ]
            }
        )


class AssessmentFeedbackSerializerTest(CacheResetTest):

    def test_serialize(self):
        feedback = AssessmentFeedback.objects.create(
            submission_uuid='abc123', feedback_text='Test feedback'
        )
        feedback.add_options(['I liked my assessment', 'I thought my assessment was unfair'])

        serialized = AssessmentFeedbackSerializer(feedback).data
        self.assertItemsEqual(serialized, {
            'submission_uuid': 'abc123',
            'feedback_text': 'Test feedback',
            'options': [
                {'text': 'I liked my assessment'},
                {'text': 'I thought my assessment was unfair'},
            ],
            'assessments': [],
        })

    def test_empty_options(self):
        feedback = AssessmentFeedback.objects.create(
            submission_uuid='abc123', feedback_text='Test feedback'
        )

        serialized = AssessmentFeedbackSerializer(feedback).data
        self.assertItemsEqual(serialized, {
            'submission_uuid': 'abc123',
            'feedback_text': 'Test feedback',
            'options': [],
            'assessments': [],
        })


class AssessmentSerializerTest(CacheResetTest):

    def test_full_assessment_dict_criteria_no_options(self):
        # Create a rubric with a criterion that has no options (just feedback)
        rubric_dict = copy.deepcopy(RUBRIC)
        rubric_dict['criteria'].append({
            'order_num': 2,
            'name': 'feedback only',
            'prompt': 'feedback only',
            'options': []
        })
        rubric = rubric_from_dict(rubric_dict)

        # Create an assessment for the rubric
        assessment = Assessment.create(rubric, "Bob", "submission UUID", "PE")
        selected = {
            u"vøȼȺƀᵾłȺɍɏ": u"𝓰𝓸𝓸𝓭",
            u"ﻭɼค๓๓คɼ": u"єχ¢єℓℓєηт",
        }
        feedback = {
            u"feedback only": u"enjoy the feedback!"
        }
        AssessmentPart.create_from_option_names(assessment, selected, feedback=feedback)

        # Serialize the assessment
        serialized = full_assessment_dict(assessment)

        # Verify that the assessment dict correctly serialized the criterion with options.
        self.assertEqual(serialized['parts'][0]['criterion']['name'], u"vøȼȺƀᵾłȺɍɏ")
        self.assertEqual(serialized['parts'][0]['option']['name'], u"𝓰𝓸𝓸𝓭")
        self.assertEqual(serialized['parts'][1]['criterion']['name'], u"ﻭɼค๓๓คɼ")
        self.assertEqual(serialized['parts'][1]['option']['name'], u"єχ¢єℓℓєηт")

        # Verify that the assessment dict correctly serialized the criterion with no options.
        self.assertIs(serialized['parts'][2]['option'], None)
        self.assertEqual(serialized['parts'][2]['criterion']['name'], u"feedback only")
