"""
Tests for team assessments.
"""
from __future__ import absolute_import

import factory

from django.contrib.auth.models import User
from django.utils.timezone import now
from freezegun import freeze_time
from factory.django import DjangoModelFactory

from openassessment.assessment.api import teams as teams_api
from openassessment.test_utils import CacheResetTest

from submissions.models import TeamSubmission
from submissions import api as submissions_api


class MockTeamSubmissionsApi():
    def create_submission_for_team(
            course_id, item_id, team_id, submitting_user_id, team_member_ids, answer,
            submitted_at=None, attempt_number=None
    ):
        student_item_dict = {
            student_id: submitting_user_id,
            item_id: item_id,
            course_id: course_id,
            item_type: "foo"
        }

        team_submission = MockTeamSubmission.create(**kwargs)
        team_submission_dict = team_submission.__dict__
        submission = submissions_api.create_submission({}, 'answer')
        team_submission_dict['submission_uuids'] = [submission]


@freeze_time("2020-04-10 12:00:01", tz_offset=-4)
class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = 'alice'
    password = 'secret'
    first_name = 'fname'
    last_name = 'lname'
    is_staff = False,
    is_active = True
    last_login = now()
    date_joined = now()


@freeze_time("2020-04-10 12:00:01", tz_offset=-4)
class MockTeamSubmission(DjangoModelFactory):
    """ Team Submission """
    class Meta:
        model = TeamSubmission

    uuid = factory.Faker('sha1')
    attempt_number = 1
    submitted_at = now()
    course_id = factory.Sequence(lambda n: 'default_course_{}'.format(n))  # pylint: disable=unnecessary-lambda
    item_id = factory.Sequence(lambda n: 'default_item_{}'.format(n))  # pylint: disable=unnecessary-lambda
    team_id = factory.Faker('sha1')
    submitted_by = factory.SubFactory(UserFactory)
    status = 'A'  # active


def _create_team_submission(self, **kwargs):
    course_id = kwargs.get('course_id', 'default_course')
    item_id = kwargs.get('item_id', 'default_item')
    team_id = kwargs.get('team_id', 'default_team_id')
    submitting_user_id = kwargs.get('team_id', 'default_team_id')
    team_member_ids = kwargs.get('team_member_ids', [1, 2, 3])
    answer = kwargs.get('answer', 'foo')
    submitted_at = kwargs.get('team_id', None),
    attempt_number = kwargs.get('attempt_number', None)

    return team_api.create_submission_for_team(
        course_id, item_id, team_id, submitting_user_id, team_member_ids, answer, submitted_at=None, attempt_number=None
    )


class TestTeamApi(CacheResetTest):
    """ Tests for the Team Assessment API """

    def test_foo(self):
        pass
