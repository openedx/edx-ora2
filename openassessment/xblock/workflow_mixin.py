"""
Handle OpenAssessment XBlock requests to the Workflow API.
"""

from xblock.core import XBlock
from openassessment.workflow import api as workflow_api
from openassessment.xblock.data_conversion import create_rubric_dict


class WorkflowMixin(object):
    """
    Handle OpenAssessment XBlock requests to the Workflow API.
    """

    # Dictionary mapping assessment names (e.g. peer-assessment)
    # to the corresponding workflow step names.
    ASSESSMENT_STEP_NAMES = {
        "example-based-assessment": "ai",
        "self-assessment": "self",
        "peer-assessment": "peer",
        "student-training": "training",
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
        ai_module = self.get_assessment_module('example-based-assessment')
        on_init_params = {
            'ai': {
                'rubric': create_rubric_dict(self.prompt, self.rubric_criteria_with_labels),
                'algorithm_id': ai_module["algorithm_id"] if ai_module else None
            }
        }
        workflow_api.create_workflow(submission_uuid, steps, on_init_params=on_init_params)

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
                "must_be_graded_by": peer_assessment_module["must_be_graded_by"],
                "track_changes": peer_assessment_module.get("track_changes", ""),
            }

        training_module = self.get_assessment_module('student-training')
        if training_module:
            requirements["training"] = {
                "num_required": len(training_module["examples"])
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
