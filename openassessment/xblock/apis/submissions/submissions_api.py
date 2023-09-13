"""
External API for ORA Submission data
"""
from copy import deepcopy
import logging

from submissions.team_api import get_team_submission

from openassessment.xblock.utils.data_conversion import (
    format_files_for_submission,
    prepare_submission_for_serialization,
    update_saved_response_format,
)
from openassessment.xblock.utils.resolve_dates import DISTANT_FUTURE
from openassessment.xblock.apis.step_data_api import StepDataAPI
from openassessment.xblock.apis.submissions.errors import (
    EmptySubmissionError,
    NoTeamToCreateSubmissionForError,
)
from openassessment.xblock.apis.submissions.file_api import FileAPI

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class SubmissionAPI(StepDataAPI):
    def __init__(self, block):
        super().__init__(block, "submission")
        self._workflow_data = block.workflow_data
        self.files = FileAPI(block, self.team_id)

    @property
    def workflow(self):
        return self.workflow_data.workflow

    # Submission Statuses

    @property
    def has_submitted(self):
        return bool(self.workflow)

    @property
    def has_been_cancelled(self):
        return self.workflow and self.workflow["status"] == "cancelled"

    @property
    def cancellation_info(self):
        if self.config_data.is_team_assignment():
            return self.workflow_data.get_team_workflow_cancellation_info(self.team_submission_uuid)
        else:
            return self.workflow_data.get_workflow_cancellation_info(self.submission_uuid)

    @property
    def has_received_final_grade(self):
        return self.workflow and self.workflow["status"] == "done"

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
        """
        Determine if student has joined a team that already submitted without them.
        They would be blocked from submitting or joining this submission.
        """
        if not self.config_data.teams_enabled:
            return False
        return not self.has_submitted and self._block.does_team_have_submission(self.team_id)

    # Submission / response data

    @property
    def has_saved(self):
        return self._block.has_saved

    @has_saved.setter
    def has_saved(self, value):
        self._block.has_saved = value

    @property
    def saved_response(self):
        """Return a saved response for a student / team when they haven't submitted"""
        return update_saved_response_format(self.config_data.saved_response)

    @saved_response.setter
    def saved_response(self, value):
        self._block.saved_response = value

    @property
    def student_submission(self):
        """Return a saved response or a student / team submission"""
        return self._block.get_user_submission(self.workflow["submission_uuid"])

    @property
    def submission_uuid(self):
        """Return a submission_uuid or None if the user hasn't submitted"""
        return self.workflow.get("submission_uuid")

    # Team Info

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
        return self.workflow.get("team_submission_uuid")

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
            response_config["rubric_criteria"] = deepcopy(self.config_data.rubric_criteria_with_labels)

        if self.due_date is not None:
            response_config["date_config_type"] = self.config_data.date_config_type

        return response_config

    # Actions

    def submission_is_empty(self, submission_dict):
        """
        Check if student_sub_dict has any submission content so that we don't
        create empty submissions.

        If there are no text responses and no file responses, raise an EmptySubmissionError

        Args:
        * submission_dict

        Returns:
        * Boolean - whether the submission is empty
        """
        has_content = False

        # Does the student_sub_dict have any non-zero-length strings in 'parts'?
        has_content |= any(part.get("text", "") for part in submission_dict.get("parts", []))

        # Are there any file_keys in student_sub_dict?
        has_content |= len(submission_dict.get("file_keys", [])) > 0

        return not has_content

    def create_submission(self, student_item_dict, submission_data):
        """Creates submission for the submitted assessment response or a list for a team assessment."""
        # Import is placed here to avoid model import at project startup.
        from submissions import api

        # Serialize the submission
        submission_dict = prepare_submission_for_serialization(submission_data)

        # Add files
        uploaded_files = self.files.get_uploads_for_submission()
        submission_dict.update(format_files_for_submission(uploaded_files))

        # Validate
        if self.submission_is_empty(submission_dict):
            raise EmptySubmissionError

        # Create submission
        submission = api.create_submission(student_item_dict, submission_dict)
        self.workflow_data.create_workflow(submission["uuid"])

        # Set student submission_uuid
        self._block.submission_uuid = submission["uuid"]

        # Emit analytics event...
        self.config_data.publish_event(
            "openassessmentblock.create_submission",
            {
                "submission_uuid": submission["uuid"],
                "attempt_number": submission["attempt_number"],
                "created_at": submission["created_at"],
                "submitted_at": submission["submitted_at"],
                "answer": submission["answer"],
            },
        )

        return submission

    def create_team_submission(self, student_item_dict, submission_data):
        """A student submitting for a team should generate matching submissions for every member of the team."""

        if not self.config_data.has_team:
            student_id = student_item_dict["student_id"]
            course_id = self.config_data.course_id
            msg = f"Student {student_id} has no team for course {course_id}"
            logger.exception(msg)
            raise NoTeamToCreateSubmissionForError(msg)

        # Import is placed here to avoid model import at project startup.
        from submissions import team_api

        team_info = self.config_data.get_team_info()

        # Serialize the submission
        submission_dict = prepare_submission_for_serialization(submission_data)

        # Add files
        uploaded_files = self.files.get_uploads_for_submission()
        submission_dict.update(format_files_for_submission(uploaded_files))

        # Validate
        if self.submission_is_empty(submission_dict):
            raise EmptySubmissionError

        submitter_anonymous_user_id = self.config_data.get_anonymous_user_id_from_xmodule_runtime()
        user = self.config_data.get_real_user(submitter_anonymous_user_id)

        anonymous_student_ids = self.config_data.get_anonymous_user_ids_for_team()
        submission = team_api.create_submission_for_team(
            self.config_data.course_id,
            student_item_dict["item_id"],
            team_info["team_id"],
            user.id,
            anonymous_student_ids,
            submission_dict,
        )

        self.workflow_data.create_team_workflow(submission["team_submission_uuid"])

        # Emit analytics event...
        self.config_data.publish_event(
            "openassessmentblock.create_team_submission",
            {
                "submission_uuid": submission["team_submission_uuid"],
                "team_id": team_info["team_id"],
                "attempt_number": submission["attempt_number"],
                "created_at": submission["created_at"],
                "submitted_at": submission["submitted_at"],
                "answer": submission["answer"],
            },
        )
        return submission
