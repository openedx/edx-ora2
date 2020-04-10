"""
Handle OpenAssessment XBlock requests around team functionality to the Workflow API.
"""

from __future__ import absolute_import

from xblock.core import XBlock
from openassessment.workflow import team_api as team_workflow_api


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
            Since we have a single submission for all students in a tean, we must query the team_submission_api (TODO)
            to return a list of sumissions for the team(s) a given student is on.

            No submission ID will be found if a team has not submitted a response

            Returns:
                (string) Submission ID if found
                (None) None if not found
        """
        if self.submission_uuid is not None:
            return self.submission_uuid

        elif self.teams_enabled:
            # TODO Once https://openedx.atlassian.net/browse/EDUCATOR-4983 is complete, modify this to use
            # the team submissions API
            from submissions.api import get_submissions, SubmissionInternalError

            try:
                # Query for submissions by the student item
                student_item = self.get_student_item_dict()
                submission_list = get_submissions(student_item)

                if submission_list and submission_list[0]["uuid"] is not None:
                    return submission_list[0]["uuid"]
            except SubmissionInternalError:
                return None

        return None

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
