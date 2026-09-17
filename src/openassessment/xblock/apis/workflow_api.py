"""
Exposed api for ORA XBlock workflows.
"""


from enum import Enum


class WorkflowAPI:
    def __init__(self, block):
        self._block = block
        self._workflow = self._block.get_workflow_info()

    def get_workflow_info(self, submission_uuid=None):
        """
        Update workflow info and return workflow for the submission.

        NOTE - Calls workflow update and caches result. When using new ORA
        experience, this needs to be called instead of the base
        get_workflow_info to update the cached value correctly.
        """
        self._workflow = self._block.get_workflow_info(submission_uuid)
        return self._workflow

    @property
    def workflow(self):
        """
        Getter for workflow, used to keep us from updating workflow every time
        we ask for info.

        NOTE - when there isn't a workflow, this will try to refresh workflow.
        """
        if not self._workflow:
            return self.get_workflow_info()
        return self._workflow

    @property
    def has_workflow(self):
        return bool(self.workflow)

    @property
    def assessment_steps(self):
        return self._block.assessment_steps

    @property
    def has_status(self):
        return bool(self.status)

    @property
    def status_details(self):
        return self.workflow.get("status_details", {})

    @property
    def next_incomplete_step(self):
        """
        Some steps (notably Peer) are "skipable" which means that the workflow auto-progresses
        past this step if there are steps after it in the workflow.

        This is, for example, to allow working on assignment requirements while waiting for peer
        grades.

        For certain circumstances, we'd like to just know the next incomplete / skipped step
        instead of auto-progressing.

        Returns:
        * "submission" when workflow doesn't exist
        * Earliest incomplete step when workflow exists
        * "done" when complete
        * "cancelled" when cancelled
        """
        step_order = self._block.rubric_assessments
        status = self.status
        status_details = self.status_details

        if not status_details:
            return "submission"

        if status in ("done", "cancelled"):
            return status

        for next_step in [step["name"] for step in step_order]:
            workflow_step_name = WorkflowStep(next_step).workflow_step_name
            step_complete = status_details[workflow_step_name].get("complete", False)
            step_graded = status_details[workflow_step_name].get("graded", False)

            if step_complete is False or step_graded is False:
                return workflow_step_name

        return "done"

    @property
    def status(self):
        if self.workflow:
            return self.workflow.get("status")
        return None

    def has_reached_given_step(self, requested_step, current_workflow_step=None):
        """
        Helper to determine if are far enough through a workflow to request data for a step.

        Returns:
        True if we are on or have skipped / completed the requested step for this ORA.
        False otherwise.
        """

        if not current_workflow_step:
            current_workflow_step = self.status or "submission"

        # Submission is start state, have always reached this
        if requested_step == "submission":
            return True

        # Have reached your current workflow step
        if requested_step == current_workflow_step:
            return True

        # Have reached any step you have completed / skipped
        step_status = self.status_details.get(requested_step, {})
        return step_status.get("complete", False) or step_status.get("skipped", False)

    @property
    def is_peer_complete(self):
        return self.status_details.get("peer", {}).get("complete", False)

    @property
    def is_peer_skipped(self):
        return self.status_details.get("peer", {}).get("skipped", False)

    @property
    def is_self_complete(self):
        return self.status_details.get("self", {}).get("complete", False)

    @property
    def is_cancelled(self):
        return self.status == "cancelled"

    @property
    def is_done(self):
        return self.status == "done"

    @property
    def is_waiting(self):
        return self.status == "waiting"

    @property
    def is_self(self):
        return self.status == "self"

    @property
    def is_training(self):
        return self.status == "training"

    @property
    def is_peer(self):
        return self.status == "peer"

    @property
    def submission_uuid(self):
        return self._block.submission_uuid

    @property
    def workflow_requirements(self):
        return self._block.workflow_requirements()

    @property
    def has_received_grade(self):
        return bool(self.workflow.get("score"))

    def get_workflow_status_counts(self):
        return self._block.get_workflow_status_counts()

    def get_workflow_cancellation_info(self, submission_uuid):
        return self._block.get_workflow_cancellation_info(submission_uuid)

    def get_course_workflow_settings(self):
        return self._block.get_course_workflow_settings()

    def update_workflow_status(self, submission_uuid=None):
        """
        Update workflow and cache result
        """
        self._block.update_workflow_status(submission_uuid)
        self._workflow = self.get_workflow_info()

    def create_workflow(self, submission_uuid):
        self._block.create_workflow(submission_uuid)

    def create_team_workflow(self, submission_uuid):
        self._block.create_team_workflow(submission_uuid)

    def get_team_workflow_info(self, team_submission_uuid=None):
        return self._block.get_team_workflow_info(team_submission_uuid)

    def get_team_submission_uuid(self):
        return self._block.get_team_submission_uuid()

    def get_team_workflow_status_counts(self):
        return self._block.get_team_workflow_status_counts()

    def get_team_workflow_cancellation_info(self, team_submission_uuid):
        return self._block.get_team_workflow_cancellation_info(team_submission_uuid)


class WorkflowStep:
    """Utility class for comparing and serializing steps"""

    # Store one disambiguated step
    canonical_step = None
    step_name = None

    # Enum of workflow steps, used for canonical mapping of steps
    class Step(Enum):
        SUBMISSION = "submission"
        PEER = "peer"
        STUDENT_TRAINING = "training"
        STAFF = "staff"
        SELF = "self"
        AI = "ai"

    _assessment_module_mappings = {
        "peer-assessment": Step.PEER,
        "student-training": Step.STUDENT_TRAINING,
        "staff-assessment": Step.STAFF,
        "self-assessment": Step.SELF,
    }

    _workflow_step_mappings = {
        "submission": Step.SUBMISSION,
        "training": Step.STUDENT_TRAINING,
        "peer": Step.PEER,
        "self": Step.SELF,
        "staff": Step.STAFF,
    }

    _step_mappings = {**_assessment_module_mappings, **_workflow_step_mappings}

    @property
    def assessment_module_name(self):
        """Get the assessment module name for the step"""
        for assessment_step, canonical_step in self._assessment_module_mappings.items():
            if canonical_step == self.canonical_step:
                return assessment_step
        return "unknown"

    @property
    def workflow_step_name(self):
        """Get the workflow step name for the step"""
        for workflow_step, canonical_step in self._workflow_step_mappings.items():
            if canonical_step == self.canonical_step:
                return workflow_step
        return "unknown"

    def __init__(self, step_name):
        # Get the "canonical" step from any representation of the step name
        self.step_name = step_name
        self.canonical_step = self._step_mappings.get(step_name)

    def __eq__(self, __value: object) -> bool:
        return self.canonical_step == self._step_mappings.get(__value)

    def __repr__(self) -> str:
        return str(self.canonical_step)
