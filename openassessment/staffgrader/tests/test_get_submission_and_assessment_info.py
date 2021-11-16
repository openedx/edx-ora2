""" Tests for the get_submission_and_assessment_info endpoint """
from contextlib import contextmanager
from typing import OrderedDict
from uuid import uuid4
import json

from mock import patch, Mock, MagicMock
from submissions import api as sub_api
from xblock.exceptions import JsonHandlerError

from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario
from openassessment.data import VersionNotFoundException
from openassessment.assessment.models.staff import StaffWorkflow
from openassessment.workflow import api as workflow_api
from openassessment.tests.factories import (
    AssessmentFactory, AssessmentPartFactory, CriterionOptionFactory, CriterionFactory
)


class GetSubmissionAndAssessmentInfoBase(XBlockHandlerTestCase):
    """ Base class for tests in this file with common setup and utility methods """
    def setUp(self):
        super().setUp()
        # Lots of large dict comparisons in this file so display full diff
        self.maxDiff = None

    @contextmanager
    def _mock_get_url_by_file_key(self, xblock):
        """ Mock the submission_mixin._get_url_by_file_key method since it relies on the backend. """
        fake_get_url = lambda file_key: f"www.file_url.com/{file_key}"

        with patch.object(xblock.__class__, '_get_url_by_file_key') as mocked_get:
            mocked_get.side_effect = fake_get_url
            yield mocked_get

    @contextmanager
    def _mock_get_submission_info(self, xblock, **kwargs):
        """ Context manager to mock get_submission_info """
        with patch.object(xblock, 'get_submission_info', **kwargs) as mocked_get:
            yield mocked_get

    @contextmanager
    def _mock_get_submission(self, **kwargs):
        """ Context manager to mock the fetching of a submission """
        with patch(
            'openassessment.staffgrader.staff_grader_mixin.get_submission',
            **kwargs
        ) as mock_get:
            yield mock_get

    @contextmanager
    def _mock_get_assessment_info(self, xblock, **kwargs):
        """ Context manager to mock get_assessment_info """
        with patch.object(xblock, 'get_assessment_info', **kwargs) as mocked_get:
            yield mocked_get

    def set_staff_user(self, xblock, staff_id):
        """
        Mock the runtime to say that the current user is course staff and is logged in as the given user.
        Additionally, mock the xblock's get_student_item_dict to return the value we want,
        rather than the values that are mocked upstream by "handle"
        """
        xblock.xmodule_runtime = Mock(user_is_staff=True)
        xblock.xmodule_runtime.anonymous_student_id = staff_id
        xblock.get_student_item_dict = Mock(return_value=self._student_item_dict(staff_id))

    def request(self, xblock, submission_id, json_format=True):  # pylint: disable=arguments-differ
        """ Helper to candle calling the `get_submission_and_assessment_info` handler """
        if submission_id is None:
            payload = {}
        else:
            payload = {'submission_id': submission_id}

        return super().request(
            xblock,
            'get_submission_and_assessment_info',
            json.dumps(payload),
            response_format='json' if json_format else None
        )

    @staticmethod
    def _student_item_dict(student_id):
        """ Generate a student_item_dict given a student_id """
        return {
            'course_id': 'TestCourseId',
            'item_id': 'TestItemId',
            'student_id': student_id,
            'item_type': 'openassessment'
        }

    @staticmethod
    def _create_student_and_submission(student, answer):
        """
        Helper method to create a student and submission for use in tests.
        """
        new_student_item = GetSubmissionAndAssessmentInfoBase._student_item_dict(student)
        submission = sub_api.create_submission(new_student_item, answer)
        workflow_api.create_workflow(submission["uuid"], ['staff'])
        return submission, new_student_item

    def submit_staff_assessment(
        self, xblock, submission_uuid, grader, option, option_2=None, criterion_feedback=None, overall_feedback=None
    ):
        """
        Helper method to submit a staff assessment
        Params:
            - xblock: (XBlock) xblock
            - student: (TestUser) the student_id whose submission we're assessing
            - grader: (TestUser) the course staff student_id who is submitting the assessment
            - option: (String) The name of the first option chosen
            - option_2: [Optional] (String) The name of the second option.
                        If not specified, use the first option again.

        Return:
            - None
        """
        assessment = {
            'options_selected': {'Criterion 1': option, 'Criterion 2': option_2 or option},
            'criterion_feedback': criterion_feedback or {},
            'overall_feedback': overall_feedback or '',
            'assess_type': 'full-grade',
            'submission_uuid': submission_uuid
        }
        self.set_staff_user(xblock, grader)
        resp = super().request(xblock, 'staff_assess', json.dumps(assessment), response_format='json')
        self.assertTrue(resp['success'])


class HandlerTests(GetSubmissionAndAssessmentInfoBase):
    """ Tests for the overall xblock handler endpoint """

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_no_submission_uuid(self, xblock):
        """ How does the endpoint behave when we don't give it a submission_uuid? """
        xblock.xmodule_runtime = Mock(user_is_staff=False)
        resp = self.request(xblock, None, json_format=False)
        self.assertIn('You do not have permission to access ORA staff grading.', resp.decode('UTF-8'))

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_no_access(self, xblock):
        """ How does the endpoint behave when the requester doesn't have proper permissions? """
        xblock.xmodule_runtime = Mock(user_is_staff=False)
        resp = self.request(xblock, 'meaningless-value', json_format=False)
        self.assertIn('You do not have permission to access ORA staff grading.', resp.decode('UTF-8'))

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_handler(self, xblock):
        """ Unit test for normal behavior of the handler endpoint """
        xblock.xmodule_runtime = MagicMock(user_is_staff=True)
        submission_uuid = str(uuid4())

        with self._mock_get_submission_info(xblock, return_value='getSubmissionInfoResult') as mocked_get_submission:
            with self._mock_get_assessment_info(xblock, return_value='getAssessmentResult') as mocked_get_assessment:
                # To mock the check in th validating decorator
                with self._mock_get_submission(return_value=True):
                    resp = self.request(xblock, submission_uuid)

        mocked_get_submission.assert_called_once_with(submission_uuid)
        mocked_get_assessment.assert_called_once_with(submission_uuid)
        self.assertDictEqual(
            resp,
            {
                'submission': mocked_get_submission.return_value,
                'assessment': mocked_get_assessment.return_value
            },
        )

    def _make_answer(self, student_id, has_files=True):
        """
        Helper method to generate a submission answer consisting of a single text response,
        and, optionally, two file responses.
        """
        result = {'parts': [{'text': f'This is the answer for learner {student_id}'}]}
        if has_files:
            result['file_keys'] = [f'key_{student_id}_{i}' for i in range(2)]
            result['files_descriptions'] = [f'description_{student_id}_{i}' for i in range(2)]
            result['files_names'] = [f'name_{student_id}_{i}' for i in range(2)]
            result['files_sizes'] = [i * 1000 for i in range(2)]
        return result

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_handler_integration__no_assessment(self, xblock):
        """ Test for full behavior of the endpoint when the requested assessment has no assessment """
        student_id = 'TestUser111'
        submission, _ = self._create_student_and_submission(student_id, self._make_answer(student_id))

        self.set_staff_user(xblock, 'Bob')
        # All we want to mock is the request to the storage backend to generate a file URL
        with self._mock_get_url_by_file_key(xblock):
            with self.assertNumQueries(1):
                resp = self.request(xblock, submission['uuid'])
        self.assertDictEqual(
            resp,
            {
                'submission': {
                    'text': [f'This is the answer for learner {student_id}'],
                    'files': [
                        {
                            'name': f'name_{student_id}_0',
                            'description': f'description_{student_id}_0',
                            'download_url': f'www.file_url.com/key_{student_id}_0'
                        },
                        {
                            'name': f'name_{student_id}_1',
                            'description': f'description_{student_id}_1',
                            'download_url': f'www.file_url.com/key_{student_id}_1'
                        },
                    ]
                },
                'assessment': {}
            }
        )

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_handler_integration__assessment(self, xblock):
        """ Test for full behavior of the endpoint when the requested assessment has an assessment """
        student_id = 'TestUser22222'
        submission, _ = self._create_student_and_submission(student_id, self._make_answer(student_id, has_files=False))
        self.submit_staff_assessment(
            xblock,
            submission['uuid'],
            'Bob',
            'Three',
            option_2="Two",
            overall_feedback="Base Assessment Feedback",
            criterion_feedback={'Criterion 1': "Feedback 1"}
        )

        self.set_staff_user(xblock, 'Bob')
        # All we want to mock is the request to the storage backend to generate a file URL
        with self._mock_get_url_by_file_key(xblock):
            with self.assertNumQueries(5):
                resp = self.request(xblock, submission['uuid'])
        self.assertDictEqual(
            resp,
            {
                'submission': {
                    'text': [f'This is the answer for learner {student_id}'],
                    'files': []
                },
                'assessment': {
                    'feedback': "Base Assessment Feedback",
                    'score': {
                        'pointsEarned': 5,
                        'pointsPossible': 6,
                    },
                    'criteria': [
                        {
                            'name': "Criterion 1",
                            'option': "Three",
                            'points': 3,
                            'feedback': "Feedback 1"
                        },
                        {
                            'name': "Criterion 2",
                            'option': "Two",
                            'points': 2,
                            'feedback': ""
                        }
                    ]
                }
            }
        )


class GetSubmissionInfoTests(GetSubmissionAndAssessmentInfoBase):
    """ Tests for the get_submission_info method """

    @contextmanager
    def _mock_parse_submission_raw_answer(self, **kwargs):
        """ Context manager to mock the parsing of a raw answer into an nswer object """
        with patch(
            'openassessment.staffgrader.staff_grader_mixin.OraSubmissionAnswerFactory.parse_submission_raw_answer',
            **kwargs
        ) as mock_parse:
            yield mock_parse

    def _mock_get_download_urls_from_submission(self, xblock, **kwargs):
        """ Helper method to mock the get_download_urls_from_submission method """
        xblock.get_download_urls_from_submission = Mock(**kwargs)

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_get_submission_error(self, xblock):
        """ What happens when there's an exception when we attempt to look up the submission? """
        submission_uuid = Mock()
        err_msg = Mock()

        with self._mock_get_submission(side_effect=sub_api.SubmissionError(err_msg)):
            with self.assertRaises(JsonHandlerError) as error_context:
                xblock.get_submission_info(submission_uuid)

        self.assertEqual(error_context.exception.status_code, 404)
        self.assertEqual(error_context.exception.message, str(err_msg))

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_answer_version_unknown(self, xblock):
        """ What happens when the raw answer we look up doesn't parse correctly? """
        submission_uuid = Mock()
        mock_submission = Mock()
        mock_exception = VersionNotFoundException("No version found!!!!11")
        with self._mock_get_submission(return_value=mock_submission) as mock_get:
            with self._mock_parse_submission_raw_answer(side_effect=mock_exception) as mock_parse:
                with self.assertRaises(JsonHandlerError) as error_context:
                    xblock.get_submission_info(submission_uuid)

        mock_get.assert_called_once_with(submission_uuid)
        mock_parse.assert_called_once_with(mock_submission.get('answer'))
        self.assertEqual(error_context.exception.status_code, 500)
        self.assertEqual(error_context.exception.message, str(mock_exception))

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_get_submission_info(self, xblock):
        """ Unit test for normal behavior of get_submission_info """
        text_responses = [
            "This is my answer for <b>Prompt One</b>.",
            "This is my answer for <i>Prompt Two</i>",
            "This is my response for <a href='www.edx.org'>Prompt Three</a>"
        ]
        file_responses = [
            dict(download_url='A', description='B', name='C'),
            dict(download_url='1', description='2', name='3'),
        ]

        submission_uuid = Mock()
        mock_submission = Mock()
        mock_answer = Mock()
        mock_answer.get_text_responses.return_value = text_responses
        with self._mock_get_submission(return_value=mock_submission):
            with self._mock_parse_submission_raw_answer(return_value=mock_answer) as mock_parse:
                self._mock_get_download_urls_from_submission(xblock, return_value=file_responses)
                submission_info = xblock.get_submission_info(submission_uuid)

        mock_parse.assert_called_once_with(mock_submission.get('answer'))
        xblock.get_download_urls_from_submission.assert_called_once_with(mock_submission)

        self.assertDictEqual(
            submission_info,
            {
                'text': text_responses,
                'files': file_responses
            }
        )

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_get_submission_info__integration(self, xblock):
        """ Test of full behavior of get_submission_info """
        student_id = 'test-student-id-1010101'
        test_answer = {
            'parts': [
                {'text': "This is my answer for <b>Prompt One</b>."},
                {'text': "This is my answer for <i>Prompt Two</i>"},
                {'text': "This is my response for <a href='www.edx.org'>Prompt Three</a>"},
            ],
            'file_keys': ['key-1', 'key-2', 'key-3'],
            'files_descriptions': ['description-1', 'description-2', 'description-3'],
            'files_names': ['filename-1', 'filename-2', 'filename-3'],
            'files_sizes': [200, 1500, 3000],
        }
        submission, _ = self._create_student_and_submission(student_id, test_answer)

        with self._mock_get_url_by_file_key(xblock):
            submission_info = xblock.get_submission_info(submission['uuid'])

        expected_submission_info = {
            'text': [
                "This is my answer for <b>Prompt One</b>.",
                "This is my answer for <i>Prompt Two</i>",
                "This is my response for <a href='www.edx.org'>Prompt Three</a>"
            ],
            'files': [
                {
                    'name': 'filename-1',
                    'description': 'description-1',
                    'download_url': 'www.file_url.com/key-1',
                },
                {
                    'name': 'filename-2',
                    'description': 'description-2',
                    'download_url': 'www.file_url.com/key-2',
                },
                {
                    'name': 'filename-3',
                    'description': 'description-3',
                    'download_url': 'www.file_url.com/key-3',
                },
            ]
        }

        self.assertDictEqual(submission_info, expected_submission_info)


class GetAssessmentInfoTests(GetSubmissionAndAssessmentInfoBase):
    def _mock_get_student_item_dict(self, xblock, course_id, item_id, student_id):
        """ Helper method to mock the lookup fo the student_item_dict """
        xblock.get_student_item_dict = Mock(
            return_value={
                'course_id': course_id,
                'item_id': item_id,
                'student_id': student_id,
            }
        )

    @contextmanager
    def _mock_get_staff_workflow(self, **kwargs):
        """ Context manager for mocking the lookup of Staff Workflows """
        with patch(
            'openassessment.staffgrader.staff_grader_mixin.StaffWorkflow.get_staff_workflow',
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

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_no_staff_workflow(self, xblock):
        """ What hppens when there's no Staff Workflow associated with a submission uuid? """
        course_id, item_id, student_id = ('TestCourse', 'TestItem', 'Bob')
        self._mock_get_student_item_dict(xblock, course_id, item_id, student_id)
        submission_uuid = str(uuid4())
        with self._mock_get_staff_workflow(side_effect=StaffWorkflow.DoesNotExist):
            with self.assertRaises(JsonHandlerError) as error_context:
                xblock.get_assessment_info(submission_uuid)

        self.assertEqual(error_context.exception.status_code, 404)
        self.assertEqual(
            error_context.exception.message,
            f"No gradeable submission found with uuid={submission_uuid} in course={course_id} item={item_id}"
        )

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_no_assessment(self, xblock):
        """ What happens when the submission uuid we provide has no associated Assessment? """
        course_id, item_id, student_id = ('TestCourse', 'TestItem', 'Bob')
        self._mock_get_student_item_dict(xblock, course_id, item_id, student_id)
        submission_uuid = str(uuid4())
        mock_staff_workflow = Mock(assessment=None)

        with self._mock_get_staff_workflow(return_value=mock_staff_workflow):
            result = xblock.get_assessment_info(submission_uuid)
        self.assertEqual(result, {})

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_no_bulk_assessments(self, xblock):
        """ What happens if `bulk_deep_fetch_assessments` returns no assessments? """
        submission_uuid = str(uuid4())
        self._test_bulk_deep_fetch_assessments_errors(xblock, submission_uuid, {})

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_multiple_bulk_assessments(self, xblock):
        """ What happens if `bulk_deep_fetch_assessments` returns multiple assessments? """
        submission_uuid = str(uuid4())
        self._test_bulk_deep_fetch_assessments_errors(
            xblock,
            submission_uuid,
            {submission_uuid: Mock(), Mock(): Mock()}
        )

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_submission_uuid_not_in_bulk_assessments(self, xblock):
        """
        What happens if `bulk_deep_fetch_assessments` returns assessments that hve a different submission uuid?
        Note: This should never happen and if it does, something's very wrong with our data. Tht said, this is an easy
        test to add in.
        """
        submission_uuid = str(uuid4())
        self._test_bulk_deep_fetch_assessments_errors(xblock, submission_uuid, {Mock: Mock()})

    def _test_bulk_deep_fetch_assessments_errors(self, xblock, submission_uuid, bulk_fetch_return_value):
        """ Helper method for tests regarding errors loading assessments """
        course_id, item_id, student_id = ('TestCourse', 'TestItem', 'Bob')
        mock_staff_workflow = Mock(assessment=str(Mock()))
        self._mock_get_student_item_dict(xblock, course_id, item_id, student_id)
        self._mock_bulk_deep_fetch_assessments(xblock, return_value=bulk_fetch_return_value)
        with self._mock_get_staff_workflow(return_value=mock_staff_workflow):
            with self.assertRaises(JsonHandlerError) as error_context:
                xblock.get_assessment_info(submission_uuid)

        self.assertEqual(error_context.exception.status_code, 500)
        self.assertEqual(error_context.exception.message, "Error looking up assessments")

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_get_assessment_info(self, xblock):
        """ Unit test for basic get_assessment_info behavior """
        course_id, item_id, student_id = ('TestCourse', 'TestItem', 'Bob')
        assessment = self._create_full_assessment()
        submission_uuid = str(uuid4())
        self._mock_get_student_item_dict(xblock, course_id, item_id, student_id)
        self._mock_bulk_deep_fetch_assessments(xblock, return_value={submission_uuid: assessment})
        with self._mock_get_staff_workflow():
            assessment_info = xblock.get_assessment_info(submission_uuid)
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

        self.assertDictEqual(assessment_info, expected_assessment_info)

    @scenario('data/simple_self_staff_scenario.xml', user_id='Bob')
    def test_get_assessment_info__integration(self, xblock):
        """ Full DB test for get_assessment_info """
        student_id = 'Bob'
        overall_feedback = 'Overall Feedback HellOTheRe'
        criterion_feedback = {'Criterion 1': "Test Crit1 Feedback"}
        submission, student_item_dict = self._create_student_and_submission(student_id, {'parts': [{'text': 'answer'}]})
        self.submit_staff_assessment(
            xblock,
            submission['uuid'],
            'Staff-1',
            'Three',
            option_2="Two",
            criterion_feedback=criterion_feedback,
            overall_feedback=overall_feedback
        )
        self._mock_get_student_item_dict(
            xblock,
            student_item_dict['course_id'],
            student_item_dict['item_id'],
            student_id
        )
        with self.assertNumQueries(5):
            # 1 - Workflow
            # 2 - Assessment
            # 3 - AssessmentPart
            # 4 - Criterion
            # 5 - Option
            assessment_info = xblock.get_assessment_info(submission['uuid'])

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

        self.assertDictEqual(assessment_info, expected_assessment_info)

    @scenario('data/feedback_only_criterion_staff.xml', user_id='Bob')
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

        course_id, item_id, student_id = ('TestCourse', 'TestItem', 'Bob')
        submission_uuid = str(uuid4())
        self._mock_get_student_item_dict(xblock, course_id, item_id, student_id)
        self._mock_bulk_deep_fetch_assessments(xblock, return_value={submission_uuid: assessment})
        with self._mock_get_staff_workflow():
            assessment_info = xblock.get_assessment_info(submission_uuid)

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

        self.assertDictEqual(assessment_info, expected_assessment_info)
