from xblock.core import XBlock
from openassessment.workflow import api as workflow_api


class WorkflowMixin(object):

    @XBlock.json_handler
    def handle_workflow_info(self, data, suffix=''):
        return self.get_workflow_info()

    def workflow_requirements(self):
        """
        Retrieve the requirements from each assessment module
        so the workflow can decide whether the student can receive a score.

        Returns:
            dict
        """
        assessment_ui_model = self.get_assessment_module('peer-assessment')

        if not assessment_ui_model:
            return {}

        return {
            "peer": {
                "must_grade": assessment_ui_model["must_grade"],
                "must_be_graded_by": assessment_ui_model["must_be_graded_by"]
            }
        }

    def update_workflow_status(self, submission_uuid=None):
        """
        Update the status of a workflow.  For example, change the status
        from peer-assessment to self-assessment.  Creates a score
        if the student has completed all requirements.

        Kwargs:
            submission_uuid (str): The submission associated with the workflow to update.
                Defaults to the submission created by the current student.

        Returns:
            None

        Raises:
            AssessmentWorkflowError
        """
        if submission_uuid is None:
            submission_uuid = self.submission_uuid

        if submission_uuid:
            requirements = self.workflow_requirements()
            workflow_api.update_from_assessments(submission_uuid, requirements)

    def get_workflow_info(self):
        """
        Retrieve a description of the student's progress in a workflow.
        Note that this *may* update the workflow status if it's changed.

        Returns:
            dict

        Raises:
            AssessmentWorkflowError
        """
        if not self.submission_uuid:
            return {}
        return workflow_api.get_workflow_for_submission(
            self.submission_uuid, self.workflow_requirements()
        )

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
        )
        num_submissions = sum(item['count'] for item in status_counts)
        return status_counts, num_submissions
