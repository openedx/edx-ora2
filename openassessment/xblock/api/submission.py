from copy import copy

from submissions.team_api import get_team_submission

from openassessment.api.problem_closed import ProblemClosedAPI
from openassessment.api.workflow import WorkflowAPI
from openassessment.xblock.data_conversion import update_saved_response_format
from openassessment.xblock.resolve_dates import DISTANT_FUTURE


class SubmissionApi:
    def __init__(self, block):
        self.block = block
        self.workflow_info = WorkflowAPI(block)
        self._workflow = self.workflow_info.workflow
        self.problem_closed_info = ProblemClosedAPI(block, step="submission")

    # Submission Statuses

    @property
    def has_submitted(self):
        return bool(self._workflow)

    @property
    def has_been_cancelled(self):
        return self._workflow and self._workflow["status"] == "cancelled"

    @property
    def cancellation_info(self):
        if self.block.teams_enabled:
            return self.block.get_team_workflow_cancellation_info(self.team_submission_uuid)
        else:
            return self.get_workflow_cancellation_info(self.submission_uuid)

    @property
    def has_received_final_grade(self):
        return self._workflow and self._workflow["status"] == "done"

    @property
    def peer_step_incomplete(self):
        return "peer" in self._workflow and not self.workflow_info.is_peer_complete

    @property
    def self_step_incomplete(self):
        return "self" in self._workflow and not self.workflow_info.is_self_complete

    # Submission Access information

    @property
    def problem_is_inaccessible(self):
        return self.problem_closed_info["problem_closed"]

    @property
    def problem_inaccessible_reason(self):
        return self.problem_closed_info["reason"]

    @property
    def problem_is_past_due(self):
        return self.problem_closed_info.is_past_due

    @property
    def problem_is_not_available_yet(self):
        return self.problem_closed_info.is_not_available_yet

    @property
    def start_date(self):
        return self.problem_closed_info.start_date

    @property
    def due_date(self):
        """A problem due in the "distant future" has, in effect no due date"""
        due_date = self.problem_closed_info["due_date"]
        if due_date < DISTANT_FUTURE:
            return due_date

    @property
    def team_previously_submitted_without_student(self):
        """"""
        if self.teams_enabled and not self.has_submitted:
            if self.does_team_have_submission(self.team_id):
                return True

    # Submission / response data

    @property
    def saved_response(self):
        """Return a saved response for a student / team when they haven't submitted"""
        return update_saved_response_format(self.block.saved_response)

    @property
    def student_submission(self):
        """Return a saved response or a student / team submission"""
        return self.block.get_user_submission(self._workflow["submission_uuid"])

    @property
    def submission_uuid(self):
        """Return a submission_uuid or None if the user hasn't submitted"""
        return self._workflow.get("submission_uuid")

    @property
    def uploaded_files(self):
        """
        Get files uploaded by users, where file uploads are enabled.

        Returns:
        * List(File descriptors) if ORA supports file uploads, can be empty.
        * None when file uploads not enabled.
        """
        if self.block.file_upload_type:
            file_urls = self.block.file_manager.file_descriptors(
                team_id=self.team_id, include_deleted=True
            )
            team_file_urls = self.block.file_manager.team_file_descriptors(team_id=self.team_id)
            return {"file_urls": file_urls, "team_file_urls": team_file_urls}

    @property
    def team_id(self):
        """
        Return the Team ID for this user / submission.

        This is either:
        1) None - when this is not a team assignment or user is not on a team
        2) The current team ID - when the active team has not yet submitted
        3) A previous team ID - the team ID associated with a previous
           submission, even if the user has since switched to a new team.

        Returns:
        * UUID or None
        """
        if self.is_team_assignment:
            if not self.has_submitted:
                return self.block.get_team_info().get("team_id")
            return get_team_submission(self.team_submission_uuid).get("team_id")

    @property
    def team_submission_uuid(self):
        return self._workflow["team_submission_uuid"]

    @property
    def team_submission_context(self):
        return self.block.get_team_submission_context()

    # Submission config

    @property
    def is_individual_assignment(self):
        return not self.is_team_assignment

    @property
    def is_team_assignment(self):
        return self.block.is_team_assignment()

    @property
    def response_config(self):
        """
        Context needed to author a response
        """
        response_config = {
            "prompts_type": self.block.prompts_type,
            # Response
            "text_response": self.block.text_response,
            "text_response_editor": self.block.text_response_editor,
            "show_rubric_during_response": self.block.show_rubric_during_response,
            "allow_latex": self.block.allow_latex,
            # File upload
            "enable_delete_files": False,
            "file_upload_response": self.block.file_upload_response,
            "file_upload_type": self.block.file_upload_type,
            "allow_multiple_files": self.block.allow_multiple_files,
        }

        if self.block.file_upload_type:
            response_config["white_listed_file_types"] = [
                "." + ext for ext in self.get_allowed_file_types_or_preset()
            ]

        if self.block.show_rubric_during_response:
            response_config["rubric_criteria"] = copy.deepcopy(
                self.block.rubric_criteria_with_labels
            )

        return response_config
