"""
Basic tests for data defaults.
"""

import ddt
from django.test import TestCase

from openassessment.xblock.utils import defaults
from openassessment.xblock.utils.validation import _is_valid_assessment_sequence as is_valid_assessment_sequence


@ddt.ddt
class DefaultAssessmentTests(TestCase):

    @ddt.data(
        (defaults.SELF_ASSESSMENT_MODULES, True),
        (defaults.PEER_ASSESSMENT_MODULES, True),
        (defaults.STAFF_ASSESSMENT_MODULES, True),
        (defaults.SELF_TO_PEER_ASSESSMENT_MODULES, True),
        (defaults.SELF_TO_STAFF_ASSESSMENT_MODULES, True),
    )
    @ddt.unpack
    def test_valid_default_assessments(self, assessments, expect_valid):
        self.assertEqual(
            is_valid_assessment_sequence(assessments),
            expect_valid
        )
