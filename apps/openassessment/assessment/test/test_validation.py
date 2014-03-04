"""
Test validation of serialized models.
"""

import ddt
from django.test import TestCase
from openassessment.assessment.serializers import validate_assessment_dict, validate_rubric_dict


@ddt.ddt
class AssessmentValidationTest(TestCase):

    @ddt.file_data('data/valid_assessments.json')
    def test_valid_assessment(self, data):
        success, msg = validate_assessment_dict(data['assessment'])
        self.assertTrue(success)
        self.assertEqual(msg, u'')

    @ddt.file_data('data/invalid_assessments.json')
    def test_invalid_assessment(self, data):
        success, msg = validate_assessment_dict(data['assessment'])
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)


@ddt.ddt
class RubricValidationTest(TestCase):

    @ddt.file_data('data/valid_rubrics.json')
    def test_valid_assessment(self, data):
        success, msg = validate_rubric_dict(data['rubric'])
        self.assertTrue(success)
        self.assertEqual(msg, u'')

    @ddt.file_data('data/invalid_rubrics.json')
    def test_invalid_assessment(self, data):
        success, msg = validate_rubric_dict(data['rubric'])
        self.assertFalse(success)
        self.assertGreater(len(msg), 0)
