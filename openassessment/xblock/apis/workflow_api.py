"""
Exposed api for ORA XBlock workflows.
"""


class WorkflowAPI:
    def __init__(self, block):
        self._block = block

    def get_workflow_info(self, submission_uuid=None):
        return self._block.get_workflow_info(submission_uuid)

    @property
    def workflow(self):
        return self.get_workflow_info()

    @property
    def has_workflow(self):
        return bool(self.workflow)

    @property
    def has_status(self):
        return bool(self.status)

    @property
    def status_details(self):
        return self.workflow.get("status_details", {})

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
        return self._block.workflow_requirements

    @property
    def status(self):
        return self.workflow.get("status")

    def get_workflow_status_counts(self):
        return self._block.get_workflow_status_counts()

    def get_workflow_cancellation_info(self, submission_uuid):
        return self._block.get_workflow_cancellation_info(submission_uuid)

    def get_course_workflow_settings(self):
        return self._block.get_course_workflow_settings()

    def update_workflow_status(self, submission_uuid=None):
        self._block.update_workflow_status(submission_uuid)

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
