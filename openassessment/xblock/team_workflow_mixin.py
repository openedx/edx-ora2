"""
Handle OpenAssessment XBlock requests around team functionality to the Workflow API.
"""

from __future__ import absolute_import

import logging

from xblock.core import XBlock
from submissions import team_api as team_sub_api
from submissions.errors import TeamSubmissionNotFoundError, TeamSubmissionInternalError
from openassessment.workflow import team_api as team_workflow_api

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class TeamWorkflowMixin:
    """
    Handle OpenAssessment, team centric XBlock requests to the Workflow API.
    """

    @XBlock.json_handler
    def handle_team_workflow_info(self, data, suffix=''):    # pylint:disable=W0613
        """
        Retrieve the current state of the workflow.

        Args:
            data: Unused

        Keyword Arguments:
            suffix: Unused

        Returns:
            dict

        """
        return self.get_team_workflow_info()

    def create_team_workflow(self, submission_uuid):
        """
        Create a new team workflow for a student submission.

        Args:
            submission_uuid (str): The UUID of the submission to associate
                with the workflow.

        Returns:
            None

        """
        team_workflow_api.create_workflow(submission_uuid)

    def get_team_workflow_info(self, team_submission_uuid=None):
        """
        Retrieve a description of the team's workflow progress in a workflow.
        Note that this *may* update the workflow status if it's changed.

        Keyword Arguments:
            team_submission_uuid (str): The team submission associated with the workflow to return.

        Returns:
            dict

        Raises:
            AssessmentWorkflowError
        """

        if team_submission_uuid is None:
            team_submission_uuid = self.get_team_submission_uuid()

        if team_submission_uuid is None:
            return {}
        return team_workflow_api.get_workflow_for_submission(team_submission_uuid)

    def get_team_submission_uuid(self):
        """
        Gets the uuid for the team submission for this user's team.

        Returns: team submission uuid if one exists, or
                 None if none exists or there was an error looking it up
        """
        if not self.has_team():
            return None

        student_item_dict = self.get_student_item_dict()
        try:
            team_submission = team_sub_api.get_team_submission_for_team(
                student_item_dict['course_id'],
                student_item_dict['item_id'],
                self.team.team_id
            )
        except (TeamSubmissionNotFoundError, TeamSubmissionInternalError):
            return None
        return team_submission['team_submission_uuid']

    def get_team_workflow_status_counts(self):
        """
        Retrieve the counts of team workflows for each status.

        Returns:
            tuple of (list, int), where the list contains dicts with keys
            "status" (unicode value) and "count" (int value), and the
            integer represents the total number of submissions.
        """
        student_item = self.get_student_item_dict()
        status_counts = team_workflow_api.get_status_counts(
            course_id=student_item['course_id'],
            item_id=student_item['item_id'],
        )
        num_submissions = sum(item['count'] for item in status_counts)
        return status_counts, num_submissions
