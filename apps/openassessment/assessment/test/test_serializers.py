import json
import os.path

from ddt import ddt, file_data
from django.test import TestCase

from openassessment.assessment.models import Criterion, CriterionOption, Rubric, AssessmentFeedback
from openassessment.assessment.serializers import (
    InvalidRubric, RubricSerializer, rubric_from_dict,
    AssessmentFeedbackSerializer
)

def json_data(filename):
    curr_dir = os.path.dirname(__file__)
    with open(os.path.join(curr_dir, filename), "rb") as json_file:
        return json.load(json_file)


class TestRubricDeserialization(TestCase):

    def test_rubric_only_created_once(self):
        # Make sure sending the same Rubric data twice only creates one Rubric,
        # and returns a reference to it the next time.
        rubric_data = json_data('rubric_data/project_plan_rubric.json')

        r1 = rubric_from_dict(rubric_data)

        with self.assertNumQueries(1):
            # Just the select -- shouldn't need the create queries
            r2 = rubric_from_dict(rubric_data)

        self.assertEqual(r1.id, r2.id)
        r1.delete()

    def test_rubric_requires_positive_score(self):
        with self.assertRaises(InvalidRubric):
            rubric_from_dict(json_data('rubric_data/no_points.json'))



class TestCriterionDeserialization(TestCase):

    def test_empty_criteria(self):
        with self.assertRaises(InvalidRubric) as cm:
            rubric_from_dict(json_data('rubric_data/empty_criteria.json'))
        self.assertEqual(
            cm.exception.errors,
            {'criteria': [u'Must have at least one criterion']}
        )

    def test_missing_criteria(self):
        with self.assertRaises(InvalidRubric) as cm:
            rubric_from_dict(json_data('rubric_data/missing_criteria.json'))
        self.assertEqual(
            cm.exception.errors,
            {'criteria': [u'This field is required.']}
        )

class TestCriterionOptionDeserialization(TestCase):

    def test_empty_options(self):
        with self.assertRaises(InvalidRubric) as cm:
            rubric_from_dict(json_data('rubric_data/empty_options.json'))
        self.assertEqual(
            cm.exception.errors,
            {
                'criteria': [
                    {},  # There are no errors in the first criterion
                    {'options': [u'Criterion must have at least one option.']}
                ]
            }
        )

    def test_missing_options(self):
        with self.assertRaises(InvalidRubric) as cm:
            rubric_from_dict(json_data('rubric_data/missing_options.json'))
        self.assertEqual(
            cm.exception.errors,
            {
                'criteria': [
                    {'options': [u'This field is required.']},
                    {}  # No errors in second criterion
                ]
            }
        )


class TestAssessmentFeedbackSerializer(TestCase):

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
