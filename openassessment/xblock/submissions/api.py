""" External api for ORA Submission data """
from copy import deepcopy

from submissions.team_api import get_team_submission

from openassessment.xblock.data_conversion import update_saved_response_format
from openassessment.xblock.resolve_dates import DISTANT_FUTURE
from openassessment.xblock.step_data_api import StepDataAPI


class SubmissionAPI(StepDataAPI):

    def __init__(self, block):
        super().__init__(block, "submission")
        self._workflow = self.workflow_data.workflow

    # Submission Statuses
    @property
    def has_submitted(self):
        return bool(self._workflow)

    @property
    def has_been_cancelled(self):
        return self._workflow and self._workflow["status"] == "cancelled"

    @property
    def cancellation_info(self):
        if self.config_data.teams_enabled:
            return self._block.get_team_workflow_cancellation_info(
                self.team_submission_uuid
            )
        else:
            return self.workflow_data.get_workflow_cancellation_info(self.submission_uuid)

    @property
    def has_received_final_grade(self):
        return self._workflow and self._workflow["status"] == "done"

    @property
    def peer_step_incomplete(self):
        return "peer" in self.workflow_data.status_details and not self.workflow_data.is_peer_complete

    @property
    def self_step_incomplete(self):
        return "self" in self.workflow_data.status_details and not self.workflow_data.is_self_complete

    # Submission Access information

    @property
    def problem_is_inaccessible(self):
        return super().problem_closed

    @property
    def problem_inaccessible_reason(self):
        return super().closed_reason

    @property
    def problem_is_past_due(self):
        return super().is_past_due

    @property
    def due_date(self):
        """A problem due in the "distant future" has, in effect no due date"""
        if super().due_date < DISTANT_FUTURE:
            return super().due_date
        return None

    @property
    def team_previously_submitted_without_student(self):
        return (self.config_data.teams_enabled and
                not self.has_submitted and
                self._block.does_team_have_submission(self.team_id))

    # Submission / response data

    @property
    def has_saved(self):
        return self._block.has_saved

    @has_saved.setter
    def has_saved(self, value):
        self._block.has_saved = value

    @property
    def saved_response(self):
        """ Return a saved response for a student / team when they haven't submitted """
        return update_saved_response_format(self.config_data.saved_response)

    @saved_response.setter
    def saved_response(self, value):
        self._block.saved_response = value

    @property
    def student_submission(self):
        """Return a saved response or a student / team submission"""
        return self._block.get_user_submission(self._workflow["submission_uuid"])

    @property
    def submission_uuid(self):
        """Return a submission_uuid or None if the user hasn't submitted"""
        return self._workflow.get("submission_uuid")

    # File Uploads

    @property
    def uploaded_files(self):
        """
        Get files uploaded by users, where file uploads are enabled.

        Returns:
        * List(File descriptors) if ORA supports file uploads, can be empty.
        * None when file uploads not enabled.
        """
        if self._block.file_upload_type:
            file_urls = self.file_manager.file_descriptors(
                team_id=self.team_id, include_deleted=True
            )
            team_file_urls = self.file_manager.team_file_descriptors(
                team_id=self.team_id
            )
            return {"file_urls": file_urls, "team_file_urls": team_file_urls}
        return None

    @property
    def saved_files_descriptions(self):
        return self._block.saved_files_descriptions

    @property
    def file_manager(self):
        return self._block.file_manager

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
                return self.config_data.get_team_info().get("team_id")
            return get_team_submission(self.team_submission_uuid).get("team_id")
        return None

    @property
    def team_submission_uuid(self):
        return self._workflow["team_submission_uuid"]

    def get_team_submission_context(self, context):
        return self._block.get_team_submission_context(context)

    # Submission config

    @property
    def is_individual_assignment(self):
        return not self.is_team_assignment

    @property
    def is_team_assignment(self):
        return self.config_data.is_team_assignment()

    @property
    def response_config(self):
        """
        Context needed to author a response
        """
        response_config = {
            "prompts_type": self.config_data.prompts_type,
            # Response
            "text_response": self.config_data.text_response,
            "text_response_editor": self.config_data.text_response_editor,
            "show_rubric_during_response": self.config_data.show_rubric_during_response,
            "allow_latex": self.config_data.allow_latex,
            # File upload
            "enable_delete_files": False,
            "file_upload_response": self.config_data.file_upload_response,
            "file_upload_type": self.config_data.file_upload_type,
            "allow_multiple_files": self.config_data.allow_multiple_files,
        }

        if self.config_data.file_upload_type:
            response_config["white_listed_file_types"] = [
                "." + ext for ext in self._block.get_allowed_file_types_or_preset()
            ]

        if self.config_data.show_rubric_during_response:
            response_config["rubric_criteria"] = deepcopy(
                self.config_data.rubric_criteria_with_labels
            )

        return response_config

    # Actions

    def create_submission(self, submission_data):
        student_item = self._block.get_student_item_dict()
        return self._block.create_submission(student_item, submission_data)

    def create_team_submission(self, submission_data):
        return self._block.create_team_submission(submission_data)
    