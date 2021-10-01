""" Tests for the Staff Workflow Listing view in the staff_grader_mixin"""

from collections import namedtuple
from contextlib import contextmanager
from datetime import datetime, time, timedelta, timezone
import json
import random

import ddt
from freezegun import freeze_time
from mock import Mock, patch
from submissions import api as sub_api

from openassessment.assessment.models.base import Assessment
from openassessment.staffgrader.models import SubmissionGradingLock
from openassessment.tests.factories import (
    AssessmentFactory, AssessmentPartFactory, CriterionOptionFactory, CriterionFactory, StaffWorkflowFactory
)
import openassessment.workflow.api as workflow_api
from openassessment.xblock.test.base import XBlockHandlerTestCase, scenario


EXPECTED_ANNOTATED_WORKFLOW_FIELDS = [
    'submission_uuid',
    'identifying_uuid',
    'created_at',
    'grading_completed_at',
    'grading_status',
    'lock_status',
    'assessment',
    'scorer_id'
]
STUDENT_ITEM = dict(
    student_id="",
    course_id="course-v1:testCourse+t5+2021T2",
    item_id="TestStaffWorkflowListView",
    item_type="openassessment",
)
ANSWER = dict(parts=['test_answer'])
STAFF_ID = "TestStaffUser"
SUBMITTED_DATE = datetime(2020, 3, 2, 12, 35, tzinfo=timezone.utc)
TEST_START_DATE = SUBMITTED_DATE + timedelta(days=2)
POINTS_POSSIBLE = 6

TestUser = namedtuple("TestUser", ['username', 'student_id', 'submission'])
MockAnnotatedStaffWorkflow = namedtuple("MockAnnotatedStaffWorkflow", EXPECTED_ANNOTATED_WORKFLOW_FIELDS)


class TestStaffWorkflowListViewBase(XBlockHandlerTestCase):
    """ Setup and helper functions for list_staff_workflow tests """

    def setUp(self):
        super().setUp()
        # A lot of this test invloves comparing fairly large dicts, so we want to be able to see the whole diff,
        # no matter what.
        self.maxDiff = None

    @classmethod
    @freeze_time(SUBMITTED_DATE)
    def setUpTestData(cls):
        cls.course_id = STUDENT_ITEM['course_id']
        # Create four TestUser learners with submissions.
        cls.students = [
            cls._create_test_user(identifier, "learner")
            for identifier in range(4)
        ]
        # Create three TestUsers to represent course staff
        cls.course_staff = [
            cls._create_test_user(identifier, "staff", create_submission=False)
            for identifier in range(3)
        ]

        # When we're mocking `get_student_ids_by_submission_uuid` and `map_anonymized_ids_to_usernames`,
        # we'll need these two dicts, so just set them up now.
        cls.student_ids_by_submission_id = {
            student.submission['uuid']: student.student_id
            for student in cls.students
        }
        cls.student_id_to_username_map = {
            test_user.student_id: test_user.username
            for test_user in cls.students + cls.course_staff
        }
        # These are just values that are going to be used several times, so also calculate them and store them now
        cls.submission_uuids = {student.submission['uuid'] for student in cls.students}

    @classmethod
    def _create_test_user(cls, identifier, user_type, create_submission=True):
        """ Create a TestUser, a namedtuple with a student_id, username, and potentially a submission """
        student_id = f"SWLV_{user_type}_{identifier}_student_id"
        if create_submission:
            student_item = cls._student_item(student_id)
            submission = sub_api.create_submission(student_item, ANSWER)
            workflow_api.create_workflow(submission["uuid"], ['staff'])
        else:
            submission = None
        return TestUser(
            username=f"SWLV_{user_type}_{identifier}_username",
            student_id=student_id,
            submission=submission,
        )

    @staticmethod
    def _student_item(student_id):
        """ Generate a student_item_dict given a student_id """
        new_student_item = STUDENT_ITEM.copy()
        new_student_item["student_id"] = student_id
        return new_student_item

    @classmethod
    def set_staff_user(cls, xblock, user=None):
        """
        Mock the runtime to say that the current user is course staff and is logged in as the given user.
        Additionally, mock the xblock's get_student_item_dict to return the value we want,
        rather than the values that are mocked upstream by "handle"
        """
        staff_id = (user or cls.course_staff[0]).student_id
        xblock.xmodule_runtime = Mock(user_is_staff=True)
        xblock.xmodule_runtime.anonymous_student_id = staff_id
        xblock.get_student_item_dict = Mock(return_value=cls._student_item(staff_id))

    @contextmanager
    def _mock_get_student_ids_by_submission_uuid(self):
        """
        Context manager that patches get_student_ids_by_submission_uuid and returns self.student_ids_by_submission_id
        """
        with patch(
            'openassessment.staffgrader.staff_grader_mixin.get_student_ids_by_submission_uuid',
            return_value=self.student_ids_by_submission_id
        ) as patched_map:
            yield patched_map

    @contextmanager
    def _mock_get_team_ids_by_team_submission_uuid(self):
        """
        Context manager that patches get_team_ids_by_team_submission_uuid.
        TODO: It currently has no real return value and is only used to assert that the function was not called.
        """
        with patch(
            'openassessment.staffgrader.staff_grader_mixin.get_team_ids_by_team_submission_uuid',
        ) as patched_map:
            yield patched_map

    @contextmanager
    def _mock_map_anonymized_ids_to_usernames(self):
        """
        Context manager that patches map_anonymized_ids_to_usernames and returns self.student_id_to_username_map
        """
        with patch(
            'openassessment.staffgrader.staff_grader_mixin.map_anonymized_ids_to_usernames',
            return_value=self.student_id_to_username_map
        ) as patched_map:
            yield patched_map

    def submit_staff_assessment(self, xblock, student, grader, option, option_2=None):
        """
        Helper method to submit a staff assessment
        Params:
            - xblock: (XBlock) xblock
            - student: (TestUser) the student whose submission we're assessing
            - grader: (TestUser) the course staff who is submitting the assessment
            - option: (String) The name of the first option chosen
            - option_2: [Optional] (String) The name of the second option.
                        If not specified, use the first option again.

        Return:
            - None
        """
        assessment = {
            'options_selected': {'Criterion 1': option, 'Criterion 2': option_2 or option},
            'criterion_feedback': {},
            'overall_feedback': '',
            'assess_type': 'full-grade',
            'submission_uuid': student.submission['uuid']
        }
        self.set_staff_user(xblock, user=grader)
        resp = self.request(xblock, 'staff_assess', json.dumps(assessment), response_format='json')
        self.assertTrue(resp['success'])

    def add_expected_response_dict(
        self,
        expected_response,
        student,
        requester=None,
        date_graded=None,
        graded_by=None,
        locked_by=None,
        expected_score=None
    ):
        """
        Helper method for constructing the expected dict returned from the listing endpoint.
        Params:
         - expected_reponse: The dict to append to
         - student: The student whose submission we're interested in
         - requester: The user requesting the list (needed for "locked" vs "in-progress") [defaults to staff_0]
         - date_graded: expected date the submission was graded [defaults to TEST_START_DATE if graded_by is non-null]
         - graded_by: expected user who created the assessment for the given submission
         - locked_by: expected owner of the current lock on the submission
         - expected_score: dict with 'points_possible' and 'points_earned'
        """
        requester = requester or self.course_staff[0]

        if date_graded is None and graded_by is not None:
            date_graded = TEST_START_DATE

        if locked_by is None:
            lock_status = 'unlocked'
        elif locked_by == requester:
            lock_status = 'in-progress'
        else:
            lock_status = 'locked'

        score = {}
        if expected_score:
            score = {
                'points_possible': POINTS_POSSIBLE,
                'points_earned': expected_score,
            }
        expected_val = {
            'submission_uuid': student.submission['uuid'],
            'dateSubmitted': str(SUBMITTED_DATE),
            'dateGraded': str(date_graded),
            'gradedBy': graded_by.username if graded_by else '',
            'gradingStatus': 'ungraded' if not date_graded else 'graded',
            'lockStatus': lock_status,
            'username': student.username,
            'score': score,
        }

        expected_response[student.submission['uuid']] = expected_val

    def setup_completed_assessments(self, xblock, grading_config):
        """
        Helper method to create assessments for submissions.
        Params:
         - xblock: xblock
         - grading_config: list of (learner_index, staff_index, option) where
                * learner_index is the index in self.students of the target learner
                * staff_index is the index in self.course_staff of the target grader
                * option is the name of an option

        The target student's submission will be assessed by the target staff,
        and given the target option for both criteria.

        Returns:
         - List of Assessment database ids for the assessments that were created
        """
        assessment_ids = []
        for student_index, staff_index, option in grading_config:
            student = self.students[student_index]
            self.submit_staff_assessment(
                xblock, student, self.course_staff[staff_index], option, option
            )
            assessment_ids.append(
                Assessment.objects.get(submission_uuid=student.submission['uuid']).id
            )
        return assessment_ids

    def setup_active_locks(self, lock_config):
        """
        Helper method to create SubmissionLocks for submissions.
        Params:
         - xblock: xblock
         - lock_config: list of (learner_index, staff_index) where
                * learner_index is the index in self.students of the target learner
                * staff_index is the index in self.course_staff of the target grader

        The target student's submission will be locked by the target staff.
        """
        for submission_index, staff_index in lock_config:
            SubmissionGradingLock.claim_submission_lock(
                self.students[submission_index].submission['uuid'],
                self.course_staff[staff_index].student_id
            )


class StaffWorkflowListViewIntegrationTests(TestStaffWorkflowListViewBase):
    """
    A series of reasonably end-to-end integration tests for the ListStaffWorkflowView endpoint.
    The only notable mock is that map_anonymized_ids_to_usernames is mocked, since we don't have a way
    to cleanly create AnonymousUserId test models.
    """

    @scenario('data/list_staff_workflows_test_scenario.xml', user_id=STAFF_ID)
    def test_no_grades_or_locks(self, xblock):
        """ Test for the result of calling the view for an ORA with no grades or locks"""
        self.set_staff_user(xblock)
        with self._mock_map_anonymized_ids_to_usernames():
            response = self.request(xblock, 'list_staff_workflows', json.dumps({}), response_format='json')
        expected_response = dict()
        for student in self.students:
            self.add_expected_response_dict(expected_response, student)

        self.assertDictEqual(response, expected_response)

    @freeze_time(TEST_START_DATE)
    @scenario('data/list_staff_workflows_test_scenario.xml', user_id=STAFF_ID)
    def test_graded(self, xblock):
        """ Test for the result of calling the view for an ORA with some grades"""
        grading_config = [(0, 0, "Three"), (1, 1, "Two"), (2, 2, "One")]
        self.setup_completed_assessments(xblock, grading_config)

        self.set_staff_user(xblock)
        with self._mock_map_anonymized_ids_to_usernames():
            response = self.request(xblock, 'list_staff_workflows', json.dumps({}), response_format='json')

        expected = dict()
        self.add_expected_response_dict(expected, self.students[0], graded_by=self.course_staff[0], expected_score=6)
        self.add_expected_response_dict(expected, self.students[1], graded_by=self.course_staff[1], expected_score=4)
        self.add_expected_response_dict(expected, self.students[2], graded_by=self.course_staff[2], expected_score=2)
        self.add_expected_response_dict(expected, self.students[3])

        self.assertDictEqual(response, expected)

    @freeze_time(TEST_START_DATE)
    @scenario('data/list_staff_workflows_test_scenario.xml', user_id=STAFF_ID)
    def test_locked(self, xblock):
        """ Test for the result of calling the view for an ORA with some locked submissions"""
        lock_config = [(0, 2), (1, 1), (2, 0)]
        self.setup_active_locks(lock_config)

        self.set_staff_user(xblock)
        with self._mock_map_anonymized_ids_to_usernames():
            response = self.request(xblock, 'list_staff_workflows', json.dumps({}), response_format='json')

        expected = dict()
        self.add_expected_response_dict(expected, self.students[0], locked_by=self.course_staff[2])
        self.add_expected_response_dict(expected, self.students[1], locked_by=self.course_staff[1])
        self.add_expected_response_dict(expected, self.students[2], locked_by=self.course_staff[0])
        self.add_expected_response_dict(expected, self.students[3])

        self.assertDictEqual(response, expected)

    @scenario('data/list_staff_workflows_test_scenario.xml', user_id='Bob')
    def test_not_staff(self, xblock):
        response = self.request(xblock, 'list_staff_workflows', '{}')
        self.assertIn(
            "You do not have permission to access ORA staff grading.",
            response.decode('utf-8')
        )

    @scenario('data/team_submission.xml', user_id=STAFF_ID)
    def test_teams(self, xblock):
        self.set_staff_user(xblock)
        with patch.object(xblock, 'is_team_assignment', return_value=True):
            response = self.request(xblock, 'list_staff_workflows', "{}", response_format='json')
        self.assertDictEqual(
            response,
            {"error": "Team Submissions not currently supported"}
        )


@ddt.ddt
class StaffWorkflowListViewUnitTests(TestStaffWorkflowListViewBase):

    @classmethod
    def setUpTestData(cls):
        """ Add some database "noise" in the form of assessments and workflows for other courses"""
        super().setUpTestData()
        for _ in range(5):
            cls.create_dummy_noise_assessment()
        cls.create_dummy_noise_staff_workflows()

    @classmethod
    def create_dummy_noise_assessment(cls):
        """ Helper method for generating a dummy Assessment, full with Parts, Options, Criteria, and a Rubric """
        assessment = AssessmentFactory.create()
        assessment_rubric = assessment.rubric
        criteria = []
        for _ in range(3):
            criterion = CriterionFactory(rubric=assessment_rubric)
            options = []
            for i in range(4):
                option = CriterionOptionFactory(criterion=criterion, points=i)
                options.append(option)
            criteria.append((criterion, options))
        for criterion, options in criteria:
            random_option = random.choice(options)
            AssessmentPartFactory.create(
                assessment=assessment,
                criterion=criterion,
                option=random_option,
            )

    @classmethod
    def create_dummy_noise_staff_workflows(cls):
        """ Create five dumy staff workflows """
        StaffWorkflowFactory.create_batch(5)

    def assert_assessment_points(self, assessment, expected_points_earned):
        """ Assert that the calculated values from an Assessment match expectations """
        self.assertEqual(assessment.points_possible, POINTS_POSSIBLE)
        self.assertEqual(assessment.points_earned, expected_points_earned)

    @scenario('data/list_staff_workflows_test_scenario.xml', user_id=STAFF_ID)
    def test_bulk_deep_fetch_assessments(self, xblock):
        """
        Unit test for bulk_deep_fetch_assessments
        """
        # Learner submission 0 graded by staff_0, 1 staff_1, 2 staff_2, 3 ungraded
        assessment_ids = self.setup_completed_assessments(xblock, [(0, 0, "Three"), (1, 1, "Two"), (2, 2, "One")])
        self.assertEqual(len(assessment_ids), 3)

        # All submissions ids except for index 3 should be included in the response
        assessed_submission_uuids = self.submission_uuids.difference({self.students[3].submission['uuid']})

        # There should be four queries:
        # - Assessments + Rubrics
        # - Assessment Parts
        # - Criteria
        # - CriterionOptions
        # We're querying starting from Assessment and going backwards against ForeignKeys,
        #  so unfortunately this can't be avoided.
        with self.assertNumQueries(4):
            assessments_by_submission_uuid = xblock.bulk_deep_fetch_assessments(assessment_ids)

        # There should be the three Assessments, and they should be the ones we expect
        self.assertEqual(len(assessments_by_submission_uuid), 3)
        self.assertEqual(
            assessed_submission_uuids,
            set(assessments_by_submission_uuid.keys())
        )

        # We should be able to calculate points_earned and points_possible for each assessment with zero additional
        # database queries
        with self.assertNumQueries(0):
            self.assert_assessment_points(assessments_by_submission_uuid[self.students[0].submission['uuid']], 6)
            self.assert_assessment_points(assessments_by_submission_uuid[self.students[1].submission['uuid']], 4)
            self.assert_assessment_points(assessments_by_submission_uuid[self.students[2].submission['uuid']], 2)

    def assert_annotated_staff_workflow_equal(self, expected, actual, i):
        """
        Assert that the actual annotated staff workflow has every field we expect,
        and that the value is what we expect
        """
        for attr in EXPECTED_ANNOTATED_WORKFLOW_FIELDS:
            self.assertTrue(hasattr(actual, attr), f"index:{i} missing attr:{attr}")
            self.assertEqual(getattr(expected, attr), getattr(actual, attr), f"index:{i} attr:{attr}")

    @ddt.data((True, True), (True, False), (False, True), (False, False))
    @ddt.unpack
    @scenario('data/list_staff_workflows_test_scenario.xml', user_id=STAFF_ID)
    @freeze_time(TEST_START_DATE)
    def test_bulk_fetch_annotated_staff_workflows(self, xblock, set_up_grades, set_up_locks):
        """ Unit test for bulk_fetch_annotated_staff_workflows """
        if set_up_grades:
            # If we are grading, student_0 graded by staff_1, student_1 ungraded,
            #  student_2 graded by staff_0, student_3 by staff_1
            assessment_ids = self.setup_completed_assessments(xblock, [(0, 1, "Two"), (2, 0, "One"), (3, 1, "Three")])
        if set_up_locks:
            # If we are locking, student_0 locked by staff_1 and student_1 locked by staff_0
            self.setup_active_locks([(0, 1), (1, 0)])
        self.set_staff_user(xblock)

        with self.assertNumQueries(1):
            annotated_workflows = xblock._bulk_fetch_annotated_staff_workflows()
            self.assertEqual(len(annotated_workflows), 4)

        # This is a bit verbose but I thought for a unit test it would be best to be explicit about test expectations
        expected_annotated_workflows = [
            MockAnnotatedStaffWorkflow(
                submission_uuid=self.students[0].submission['uuid'],
                identifying_uuid=self.students[0].submission['uuid'],
                created_at=SUBMITTED_DATE,
                grading_completed_at=TEST_START_DATE if set_up_grades else None,
                grading_status='graded' if set_up_grades else 'ungraded',
                lock_status='locked' if set_up_locks else 'unlocked',
                assessment=str(assessment_ids[0]) if set_up_grades else None,
                scorer_id=self.course_staff[1].student_id if set_up_grades else '',
            ),
            MockAnnotatedStaffWorkflow(
                submission_uuid=self.students[1].submission['uuid'],
                identifying_uuid=self.students[1].submission['uuid'],
                created_at=SUBMITTED_DATE,
                grading_completed_at=None,
                grading_status='ungraded',
                lock_status='in-progress' if set_up_locks else 'unlocked',
                assessment=None,
                scorer_id='',
            ),
            MockAnnotatedStaffWorkflow(
                submission_uuid=self.students[2].submission['uuid'],
                identifying_uuid=self.students[2].submission['uuid'],
                created_at=SUBMITTED_DATE,
                grading_completed_at=TEST_START_DATE if set_up_grades else None,
                grading_status='graded' if set_up_grades else 'ungraded',
                lock_status='unlocked',
                assessment=str(assessment_ids[1]) if set_up_grades else None,
                scorer_id=self.course_staff[0].student_id if set_up_grades else '',
            ),
            MockAnnotatedStaffWorkflow(
                submission_uuid=self.students[3].submission['uuid'],
                identifying_uuid=self.students[3].submission['uuid'],
                created_at=SUBMITTED_DATE,
                grading_completed_at=TEST_START_DATE if set_up_grades else None,
                grading_status='graded' if set_up_grades else 'ungraded',
                lock_status='unlocked',
                assessment=str(assessment_ids[2]) if set_up_grades else None,
                scorer_id=self.course_staff[1].student_id if set_up_grades else '',
            )
        ]
        with self.assertNumQueries(0):
            for i, (expected, actual) in enumerate(zip(expected_annotated_workflows, annotated_workflows)):
                self.assert_annotated_staff_workflow_equal(expected, actual, i)

    @scenario('data/list_staff_workflows_test_scenario.xml', user_id=STAFF_ID)
    @freeze_time(TEST_START_DATE)
    def test_staff_workflows_to_api_format(self, xblock):
        """ Unit test for staff_workflows_to_api_format """
        self.set_staff_user(xblock)
        # Set up the mock return_value for bulk_deep_fetch_assessments.
        # submissions 0 and 3 are the only ones assessed
        mock_assessments_map = {
            self.students[0].submission['uuid']: Mock(points_earned=5, points_possible=10),
            self.students[3].submission['uuid']: Mock(points_earned=6, points_possible=10)
        }
        mock_staff_workflows = [
            MockAnnotatedStaffWorkflow(
                submission_uuid=self.students[0].submission['uuid'],
                identifying_uuid=self.students[0].submission['uuid'],
                created_at=SUBMITTED_DATE,
                grading_completed_at=TEST_START_DATE,
                grading_status='graded',
                lock_status='unlocked',
                assessment='assessment-1',
                scorer_id=self.course_staff[1].student_id,
            ),
            MockAnnotatedStaffWorkflow(
                submission_uuid=self.students[1].submission['uuid'],
                identifying_uuid=self.students[1].submission['uuid'],
                created_at=SUBMITTED_DATE,
                grading_completed_at=None,
                grading_status='ungraded',
                lock_status='locked',
                assessment=None,
                scorer_id='',
            ),
            MockAnnotatedStaffWorkflow(
                submission_uuid=self.students[2].submission['uuid'],
                identifying_uuid=self.students[2].submission['uuid'],
                created_at=SUBMITTED_DATE,
                grading_completed_at=None,
                grading_status='ungraded',
                lock_status='in-progress',
                assessment=None,
                scorer_id='',
            ),
            MockAnnotatedStaffWorkflow(
                submission_uuid=self.students[3].submission['uuid'],
                identifying_uuid=self.students[3].submission['uuid'],
                created_at=SUBMITTED_DATE,
                grading_completed_at=TEST_START_DATE + timedelta(days=4),
                grading_status='graded',
                lock_status='locked',
                assessment='assessment-2',
                scorer_id=self.course_staff[2].student_id,
            ),
        ]
        with self._mock_get_student_ids_by_submission_uuid() as mock_get_student_ids:
            with self._mock_get_team_ids_by_team_submission_uuid() as mock_get_team_ids:
                with self._mock_map_anonymized_ids_to_usernames() as mock_map_ids:
                    with patch.object(xblock, 'bulk_deep_fetch_assessments') as mock_bulk_fetch_assessments:
                        mock_bulk_fetch_assessments.return_value = mock_assessments_map
                        response = xblock.staff_workflows_to_api_format(mock_staff_workflows)

        mock_get_student_ids.assert_called_once_with(
            self.course_id,
            self.submission_uuids
        )
        mock_get_team_ids.assert_not_called()
        # We only expect to look up the learner student_ids and the student_ids of the staff that assessed submissions.
        # The other two shouldn't be included.
        expected_anonymous_id_lookups = set(student.student_id for student in self.students)
        expected_anonymous_id_lookups.update(
            {self.course_staff[1].student_id, self.course_staff[2].student_id}
        )
        mock_map_ids.assert_called_once_with(expected_anonymous_id_lookups)
        mock_bulk_fetch_assessments.assert_called_once_with({'assessment-1', 'assessment-2'})

        # Again, verbose, but better to be explicit in unit test expectations.
        expected_response = {
            self.students[0].submission['uuid']: {
                'dateGraded': str(TEST_START_DATE),
                'dateSubmitted': str(SUBMITTED_DATE),
                'gradedBy': self.course_staff[1].username,
                'gradingStatus': 'graded',
                'lockStatus': 'unlocked',
                'score': {
                    'points_earned': 5,
                    'points_possible': 10
                },
                'submission_uuid': self.students[0].submission['uuid'],
                'username': self.students[0].username
            },
            self.students[1].submission['uuid']: {
                'dateGraded': 'None',
                'dateSubmitted': str(SUBMITTED_DATE),
                'gradedBy': '',
                'gradingStatus': 'ungraded',
                'lockStatus': 'locked',
                'score': {},
                'submission_uuid': self.students[1].submission['uuid'],
                'username': self.students[1].username
            },
            self.students[2].submission['uuid']: {
                'dateGraded': 'None',
                'dateSubmitted': str(SUBMITTED_DATE),
                'gradedBy': '',
                'gradingStatus': 'ungraded',
                'lockStatus': 'in-progress',
                'score': {},
                'submission_uuid': self.students[2].submission['uuid'],
                'username': self.students[2].username
            },
            self.students[3].submission['uuid']: {
                'dateGraded': str(TEST_START_DATE + timedelta(days=4)),
                'dateSubmitted': str(SUBMITTED_DATE),
                'gradedBy': self.course_staff[2].username,
                'gradingStatus': 'graded',
                'lockStatus': 'locked',
                'score': {
                    'points_earned': 6,
                    'points_possible': 10
                },
                'submission_uuid': self.students[3].submission['uuid'],
                'username': self.students[3].username
            },
        }

        self.assertDictEqual(response, expected_response)
