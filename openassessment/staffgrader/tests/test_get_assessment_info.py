""" Tests for the get_assessment_info handler"""

from contextlib import contextmanager
from collections import OrderedDict

from uuid import uuid4
from mock import patch, Mock

from openassessment.staffgrader.tests.test_base import StaffGraderMixinTestBase
from openassessment.tests.factories import (
    AssessmentFactory, AssessmentPartFactory, CriterionFactory, CriterionOptionFactory
)
from openassessment.assessment.models.staff import StaffWorkflow
from openassessment.xblock.test.base import scenario


class GetAssessmentInfoTests(StaffGraderMixinTestBase):
    """ Tests for the get_assessment_info handler"""
    handler_name = 'get_assessment_info'

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob', is_staff=True)
    def test_no_submission_uuid(self, xblock):
        """ How does the endpoint behave when we don't give it a submission_uuid? """
        response = self.request(xblock, {})
        self.assert_response(response, 400, {"error": "Body must contain a submission_uuid"})

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob', is_staff=True)
    def test_no_access(self, xblock):
        """ How does the endpoint behave when the requester doesn't have proper permissions? """
        response = self.request(xblock, {'submission_uuid': 'meaningless-value'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('You do not have permission to access ORA staff grading.', response.body.decode('UTF-8'))

    @contextmanager
    def _mock_get_staff_workflow(self, **kwargs):
        """ Context manager for mocking the lookup of Staff Workflows """
        with patch(
            'openassessment.staffgrader.staff_grader_mixin.StaffWorkflow.get_staff_workflow',
            **kwargs
        ) as mock_get:
            yield mock_get

    @contextmanager
    def _mock_get_team_staff_workflow(self, **kwargs):
        """ Context manager for mocking the lookup of Team Staff Workflows """
        with patch(
            'openassessment.staffgrader.staff_grader_mixin.TeamStaffWorkflow.get_team_staff_workflow',
            **kwargs
        ) as mock_get:
            yield mock_get

    def _mock_get_download_urls_from_submission(self, xblock, **kwargs):
        """ Helper method to mock getting uploaded file info from a submission"""
        xblock.get_download_urls_from_submission = Mock(**kwargs)

    def _mock_bulk_deep_fetch_assessments(self, xblock, **kwargs):
        """ Helper method to mock the loading of assessment info """
        xblock.bulk_deep_fetch_assessments = Mock(**kwargs)

    def _create_full_assessment(self):
        """ Helper method for generating a dummy Assessment, full with Parts, Options, Criteria, and a Rubric """
        assessment = AssessmentFactory.create(feedback="Base Assessment Feedback")
        assessment_rubric = assessment.rubric
        criteria = []
        for _ in range(3):
            criterion = CriterionFactory(rubric=assessment_rubric)
            options = []
            for i in range(4):
                option = CriterionOptionFactory(criterion=criterion, points=i + 1)
                options.append(option)
            criteria.append((criterion, options))
        for i, (criterion, options) in enumerate(criteria):
            option = options[i]  # Different point value for each criterion
            AssessmentPartFactory.create(
                assessment=assessment,
                criterion=criterion,
                option=option,
                feedback=f"Feedback for criterion={criterion.id}"
            )
        return assessment

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob', is_staff=True)
    def test_no_staff_workflow(self, xblock):
        """ What hppens when there's no Staff Workflow associated with a submission uuid? """
        submission_uuid = str(uuid4())
        with self._mock_get_staff_workflow(side_effect=StaffWorkflow.DoesNotExist):
            with self._mock_get_submission():
                response = self.request(xblock, {'submission_uuid': submission_uuid})

        self.assert_response(
            response,
            404,
            {
                'error': (
                    f"No gradeable submission found with uuid={submission_uuid} in course={xblock.course_id}"
                    f" item={xblock.item_id}"
                )
            }
        )

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob', is_staff=True)
    def test_no_assessment(self, xblock):
        """ What happens when the submission uuid we provide has no associated Assessment? """
        submission_uuid = str(uuid4())
        mock_staff_workflow = Mock(assessment=None)

        with self._mock_get_staff_workflow(return_value=mock_staff_workflow):
            with self._mock_get_submission():
                response = self.request(xblock, {'submission_uuid': submission_uuid})

        self.assert_response(response, 200, {})

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob', is_staff=True)
    def test_multiple_bulk_assessments(self, xblock):
        """ What happens if `bulk_deep_fetch_assessments` returns multiple assessments? """
        submission_uuid = str(uuid4())
        mock_staff_workflow = Mock(assessment=str(Mock()))
        self._mock_bulk_deep_fetch_assessments(xblock, return_value={submission_uuid: Mock(), Mock(): Mock()})
        with self._mock_get_staff_workflow(return_value=mock_staff_workflow):
            with self._mock_get_submission():
                response = self.request(xblock, {'submission_uuid': submission_uuid})

        self.assert_response(response, 500, {'error': 'Error looking up assessments'})

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob', is_staff=True)
    def test_get_assessment_info(self, xblock):
        """ Unit test for basic get_assessment_info behavior """
        assessment = self._create_full_assessment()
        submission_uuid = str(uuid4())
        self._mock_bulk_deep_fetch_assessments(xblock, return_value={submission_uuid: assessment})
        with self._mock_get_staff_workflow():
            with self._mock_get_submission():
                response = self.request(xblock, {'submission_uuid': submission_uuid})

        expected_assessment_info = {
            'feedback': "Base Assessment Feedback",
            'score': {
                'pointsEarned': 6,
                'pointsPossible': 12,
            },
            'criteria': [
                OrderedDict({
                    'name': part.criterion.name,
                    'option': part.option.name,
                    'points': part.option.points,
                    'feedback': f"Feedback for criterion={part.criterion.id}"
                }) for part in assessment.parts.all()
            ]
        }

        self.assert_response(response, 200, expected_assessment_info)

    @scenario('data/simple_self_staff_scenario.xml', user_id='Staff 1', is_staff=True)
    def test_get_assessment_info__integration(self, xblock):
        """ Full DB test for get_assessment_info """
        overall_feedback = 'Overall Feedback HellOTheRe'
        criterion_feedback = {'Criterion 1': "Test Crit1 Feedback"}
        submission, _ = self._create_student_and_submission('Bob', {'parts': [{'text': 'answer'}]})
        self.submit_staff_assessment(
            xblock,
            submission['uuid'],
            'Three',
            option_2="Two",
            criterion_feedback=criterion_feedback,
            overall_feedback=overall_feedback
        )
        with self.assertNumQueries(5):
            # 1 - Workflow
            # 2 - Assessment
            # 3 - AssessmentPart
            # 4 - Criterion
            # 5 - Option
            response = self.request(xblock, {'submission_uuid': submission['uuid']})

        expected_assessment_info = {
            'feedback': overall_feedback,
            'score': OrderedDict({
                'pointsEarned': 5,
                'pointsPossible': 6,
            }),
            'criteria': [
                OrderedDict({
                    'name': 'Criterion 1',
                    'option': 'Three',
                    'points': 3,
                    'feedback': criterion_feedback['Criterion 1']
                }),
                OrderedDict({
                    'name': 'Criterion 2',
                    'option': 'Two',
                    'points': 2,
                    'feedback': ''
                }),
            ]
        }

        self.assert_response(response, 200, expected_assessment_info)

    @scenario('data/feedback_only_criterion_staff.xml', user_id='Bob', is_staff=True)
    def test_get_assessment_info__feedback_only(self, xblock):
        """ Unit test for get_assessment_info for a feedback-only Criterion """
        # Create an Assessment with multiple parts that are feedback-only
        assessment = AssessmentFactory.create(feedback="Base Assessment Feedback")
        assessment_rubric = assessment.rubric
        for _ in range(3):
            criterion = CriterionFactory(rubric=assessment_rubric)
            AssessmentPartFactory.create(
                assessment=assessment,
                criterion=criterion,
                feedback=f"Feedback for criterion {criterion.id}"
            )

        submission_uuid = str(uuid4())
        self._mock_bulk_deep_fetch_assessments(xblock, return_value={submission_uuid: assessment})
        with self._mock_get_staff_workflow():
            with self._mock_get_submission():
                response = self.request(xblock, {'submission_uuid': submission_uuid})

        expected_assessment_info = {
            'feedback': "Base Assessment Feedback",
            'score': {
                'pointsEarned': 0,
                'pointsPossible': 0,
            },
            'criteria': [
                OrderedDict({
                    'name': part.criterion.name,
                    'option': None,
                    'points': None,
                    'feedback': f"Feedback for criterion {part.criterion.id}"
                }) for part in assessment.parts.all()
            ]
        }

        self.assert_response(response, 200, expected_assessment_info)
