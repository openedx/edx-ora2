"""
Handle OpenAssessment XBlock requests to the Workflow API.
"""

from xblock.core import XBlock
from submissions.api import get_submissions, SubmissionInternalError, SubmissionNotFoundError

from openassessment.workflow import api as workflow_api
from openassessment.workflow.models import AssessmentWorkflowCancellation


class WorkflowMixin:
    """
    Handle OpenAssessment XBlock requests to the Workflow API.
    """

    # Dictionary mapping assessment names (e.g. peer-assessment)
    # to the corresponding workflow step names.
    ASSESSMENT_STEP_NAMES = {
        "self-assessment": "self",
        "peer-assessment": "peer",
        "student-training": "training",
        "staff-assessment": "staff"
    }

    @XBlock.json_handler
    def handle_workflow_info(self, data, suffix=''):    # pylint:disable=W0613
        """
        Retrieve the current state of the workflow.

        Args:
            data: Unused

        Keyword Arguments:
            suffix: Unused

        Returns:
            dict

        """
        return self.get_workflow_info()

    def create_workflow(self, submission_uuid):
        """
        Create a new workflow for a student submission.

        Args:
            submission_uuid (str): The UUID of the submission to associate
                with the workflow.

        Returns:
            None

        """
        steps = self._create_step_list()
        workflow_api.create_workflow(submission_uuid, steps, on_init_params={})

    def workflow_requirements(self):
        """
        Retrieve the requirements from each assessment module
        so the workflow can decide whether the student can receive a score.

        Returns:
            dict

        """
        requirements = {}

        peer_assessment_module = self.get_assessment_module('peer-assessment')
        if peer_assessment_module:
            requirements["peer"] = {
                "must_grade": peer_assessment_module["must_grade"],
                "must_be_graded_by": peer_assessment_module["must_be_graded_by"]
            }

        training_module = self.get_assessment_module('student-training')
        if training_module:
            requirements["training"] = {
                "num_required": len(training_module["examples"])
            }

        staff_assessment_module = self.get_assessment_module('staff-assessment')
        if staff_assessment_module:
            requirements["staff"] = {
                "required": staff_assessment_module["required"]
            }

        return requirements

    def update_workflow_status(self, submission_uuid=None):
        """
        Update the status of a workflow.  For example, change the status
        from peer-assessment to self-assessment.  Creates a score
        if the student has completed all requirements.

        Keyword Arguments:
            submission_uuid (str): The submission associated with the workflow to update.
                Defaults to the submission created by the current student.

        Returns:
            None

        Raises:
            AssessmentWorkflowError
        """
        if submission_uuid is None:
            submission_uuid = self.submission_uuid

        if submission_uuid is not None:
            requirements = self.workflow_requirements()
            workflow_api.update_from_assessments(submission_uuid, requirements)

    def get_workflow_info(self, submission_uuid=None):
        """
        Retrieve a description of the student's progress in a workflow.
        Note that this *may* update the workflow status if it's changed.

        Keyword Arguments:
            submission_uuid (str): The submission associated with the workflow to return.
                Defaults to the submission created by the current student.

        Returns:
            dict

        Raises:
            AssessmentWorkflowError
        """
        if self.is_team_assignment():
            if submission_uuid:
                team_submission_uuid = self.get_team_submission_uuid_from_individual_submission_uuid(submission_uuid)
            else:
                team_submission_uuid = None
            return self.get_team_workflow_info(team_submission_uuid)

        if submission_uuid is None:
            submission_uuid = self.get_submission_uuid()

        if submission_uuid is None:
            return {}
        return workflow_api.get_workflow_for_submission(
            submission_uuid, self.workflow_requirements()
        )

    def get_submission_uuid(self):
        """ Submission UUIDs can be in multiple spots based on the submission type,
            try the various locations to try to find it.

            No submission ID will be found if a learner has not submitted a response

            Indiviual submissions will be in the user's context.

            Returns:
                (string) Submission ID if found
                (None) None if not found
        """
        if self.submission_uuid is not None:
            return self.submission_uuid
        elif self.is_team_assignment():
            try:
                # Query for submissions by the student item
                student_item = self.get_student_item_dict()
                submission_list = get_submissions(student_item)
                if submission_list and submission_list[0]["uuid"] is not None:
                    return submission_list[0]["uuid"]
            except (SubmissionInternalError, SubmissionNotFoundError):
                return None
        return None

    def get_workflow_status_counts(self):
        """
        Retrieve the counts of students in each step of the workflow.

        Returns:
            tuple of (list, int), where the list contains dicts with keys
            "status" (unicode value) and "count" (int value), and the
            integer represents the total number of submissions.

        Example Usage:
            >>> status_counts, num_submissions = xblock.get_workflow_status_counts()
            >>> num_submissions
                12
            >>> status_counts
                [
                    {"status": "peer", "count": 2},
                    {"status": "self", "count": 1},
                    {"status": "waiting": "count": 4},
                    {"status": "done", "count": 5}
                ]
        """
        student_item = self.get_student_item_dict()
        status_counts = workflow_api.get_status_counts(
            course_id=student_item['course_id'],
            item_id=student_item['item_id'],
            steps=self._create_step_list(),
        )
        num_submissions = sum(item['count'] for item in status_counts)
        return status_counts, num_submissions

    def _create_step_list(self):
        """
        Return a list of valid workflow step names.
        This translates between the assessment types (loaded from the problem definition)
        and the step types (used by the Workflow API).
        At some point, we should probably refactor to make these two names consistent.

        Returns:
            list

        """
        return [
            self.ASSESSMENT_STEP_NAMES.get(ra['name'])
            for ra in self.valid_assessments
            if ra['name'] in self.ASSESSMENT_STEP_NAMES
        ]

    def get_workflow_cancellation_info(self, submission_uuid):
        """
        Returns cancellation information for a particular submission.

        :param submission_uuid: The submission to return information for.
        :return: The cancellation information, or None if the submission has
        not been cancelled.
        """
        cancellation_info = workflow_api.get_assessment_workflow_cancellation(submission_uuid)
        if not cancellation_info:
            return None

        # Add the username of the staff member who cancelled the submission
        cancellation_info['cancelled_by'] = self.get_username(cancellation_info['cancelled_by_id'])

        # Add the date that the workflow was cancelled (in preference to the serialized date string)
        del cancellation_info['created_at']
        cancellation_model = AssessmentWorkflowCancellation.get_latest_workflow_cancellation(submission_uuid)
        if cancellation_model:
            cancellation_info['cancelled_at'] = cancellation_model.created_at

        return cancellation_info
