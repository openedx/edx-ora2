"""
Tests for team assessments.
"""
from __future__ import absolute_import

from openassessment.assessment.api import teams as teams_api
from openassessment.test_utils import CacheResetTest


class TestTeamApi(CacheResetTest):
    """ Tests for the Team Assessment API """

    def test_submitter_is_finished(self):
        team_submission_uuid = 'foo'
        team_requirements = {}

        self.assertTrue(teams_api.submitter_is_finished(
            team_submission_uuid,
            team_requirements
        ))
