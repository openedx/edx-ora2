# -*- coding: utf-8 -*-
"""
Tests for staff assessment handlers in Open Assessment XBlock.
"""
import json
import mock
import copy
from openassessment.assessment.api import staff as staff_api
from openassessment.xblock.data_conversion import create_rubric_dict
from .base import XBlockHandlerTestCase, scenario


class StaffAssessmentTestBase(XBlockHandlerTestCase):
    maxDiff = None

    SUBMISSION = (u'ՇﻉรՇ', u'รપ๒๓ٱรรٱѻก')

    ASSESSMENT = {
        'options_selected': {u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮': u'ﻉซƈﻉɭɭﻉกՇ', u'Form': u'Fair'},
        'criterion_feedback': {},
        'overall_feedback': ""
    }

    def set_staff_access(self, xblock):
        xblock.xmodule_runtime = mock.Mock(user_is_staff=True)
        xblock.xmodule_runtime.anonymous_student_id = 'Bob'


class TestStaffAssessment(StaffAssessmentTestBase):

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_staff_assess_handler(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        # Submit a staff-assessment
        self.set_staff_access(xblock)
        self.ASSESSMENT['submission_uuid'] = submission['uuid']
        resp = self.request(xblock, 'staff_assess', json.dumps(self.ASSESSMENT), response_format='json')
        self.assertTrue(resp['success'])

        # Expect that a staff-assessment was created
        assessment = staff_api.get_latest_assessment(submission['uuid'])
        self.assertEqual(assessment['submission_uuid'], submission['uuid'])
        self.assertEqual(assessment['points_earned'], 5)
        self.assertEqual(assessment['points_possible'], 6)
        self.assertEqual(assessment['scorer_id'], 'Bob')
        self.assertEqual(assessment['score_type'], 'ST')
        self.assertEqual(assessment['feedback'], u'')

        parts = sorted(assessment['parts'])
        self.assertEqual(len(parts), 2)
        self.assertEqual(parts[0]['option']['criterion']['name'], u'Form')
        self.assertEqual(parts[0]['option']['name'], 'Fair')
        self.assertEqual(parts[1]['option']['criterion']['name'], u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮')
        self.assertEqual(parts[1]['option']['name'], u'ﻉซƈﻉɭɭﻉกՇ')

        # get the assessment scores by criteria
        assessment_by_crit = staff_api.get_assessment_scores_by_criteria(submission["uuid"])
        self.assertEqual(assessment_by_crit[u'𝓒𝓸𝓷𝓬𝓲𝓼𝓮'], 3)
        self.assertEqual(assessment_by_crit[u'Form'], 2)

        score = staff_api.get_score(submission["uuid"], None)
        self.assertEqual(assessment['points_earned'], score['points_earned'])
        self.assertEqual(assessment['points_possible'], score['points_possible'])

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_staff_assess_permission_error(self, xblock):
        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        xblock.create_submission(student_item, self.SUBMISSION)
        resp = self.request(xblock, 'staff_assess', json.dumps(self.ASSESSMENT))
        self.assertIn("You do not have permission", resp)

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_staff_assess_invalid_options(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        self.set_staff_access(xblock)
        self.ASSESSMENT['submission_uuid'] = submission['uuid']

        for key in self.ASSESSMENT:
            assessment_copy = copy.copy(self.ASSESSMENT)
            del assessment_copy[key]
            resp = self.request(xblock, 'staff_assess', json.dumps(assessment_copy), response_format='json')
            self.assertFalse(resp['success'])
            self.assertIn('msg', resp)

    @scenario('data/self_assessment_scenario.xml', user_id='bob')
    def test_staff_assess_assessment_error(self, xblock):
        student_item = xblock.get_student_item_dict()

        # Create a submission for the student
        submission = xblock.create_submission(student_item, self.SUBMISSION)

        self.set_staff_access(xblock)
        self.ASSESSMENT['submission_uuid'] = submission['uuid']
        with mock.patch('openassessment.xblock.staff_assessment_mixin.staff_api') as mock_api:
            #  Simulate a error
            mock_api.create_assessment.side_effect = staff_api.StaffAssessmentRequestError
            resp = self.request(xblock, 'staff_assess', json.dumps(self.ASSESSMENT), response_format='json')
            self.assertFalse(resp['success'])
            self.assertIn('msg', resp)

            #  Simulate a different error
            mock_api.create_assessment.side_effect = staff_api.StaffAssessmentInternalError
            resp = self.request(xblock, 'staff_assess', json.dumps(self.ASSESSMENT), response_format='json')
            self.assertFalse(resp['success'])
            self.assertIn('msg', resp)


class TestStaffAssessmentRender(StaffAssessmentTestBase):
    #TODO: test success when staff assessment template exists

    @scenario('data/self_assessment_scenario.xml', user_id='Bob')
    def test_render_staff_assessment_permission_error(self, xblock):
        # Create a submission for the student
        student_item = xblock.get_student_item_dict()
        xblock.create_submission(student_item, self.SUBMISSION)
        resp = self.request(xblock, 'render_staff_assessment', json.dumps(self.ASSESSMENT))
        self.assertIn("You do not have permission", resp)
