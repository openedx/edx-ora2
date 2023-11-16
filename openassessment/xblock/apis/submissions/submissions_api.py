"""
External API for ORA Submission data
"""
from copy import deepcopy
import logging

from submissions.api import get_submission
from submissions.team_api import get_team_submission
from openassessment.data import OraSubmissionAnswerFactory


from openassessment.xblock.utils.data_conversion import (
    create_submission_dict,
    update_saved_response_format,
)
from openassessment.xblock.utils.resolve_dates import DISTANT_FUTURE
from openassessment.xblock.apis.step_data_api import StepDataAPI
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
        return bool(self.workflow) and self.workflow["status"] == "cancelled"

    @property
    def cancellation_info(self):
        if self.config_data.is_team_assignment():
            return self.workflow_data.get_team_workflow_cancellation_info(self.team_submission_uuid)
        else:
            return self.workflow_data.get_workflow_cancellation_info(self.submission_uuid)

    def _safe_get_cancellation_info_field(self, field):
        cancellation_info = self.cancellation_info
        if cancellation_info is None:
            return None
        return cancellation_info.get(field)

    @property
    def cancelled_by(self):
        return self._safe_get_cancellation_info_field('cancelled_by')

    @property
    def cancelled_at(self):
        return self._safe_get_cancellation_info_field('cancelled_at')

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

    @property
    def saved_response_submission_dict(self):
        """Return the current saved response in an expected format"""
        return create_submission_dict(
            self.saved_response,
            self.config_data.prompts
        )

    def get_submission(self, submission_uuid):
        """
        Get a serialized representation of an ORA submission.
        Returns:
            {
                "text_responses": (list) [text responses]
                "uploaded_files": (list) [
                    {
                        "download_url": (url)
                        "description": (str)
                        "name": (str)
                        "size": (int)
                    }
                ]
            }

        Raises:
            submissions.errors.SubmissionError: If there was an error loading the submission
            openassessment.data.VersionNotFoundException: If the submission did not match any known
                                                          ORA answer version
        """
        submission = get_submission(submission_uuid)
        return OraSubmissionAnswerFactory.parse_submission_raw_answer(submission.get('answer'))

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

    def get_submission_team_info(self, workflow):
        """
        Returns tuple (team info, team ID)
        """
        if not self.is_team_assignment:
            return {}, None

        team_info = self.config_data.get_team_info(staff_or_preview_data=False)
        if team_info is None:
            team_info = {}

        # Get the id of the team the learner is currently on
        team_id = team_info.get('team_id', None)
        if team_id:
            # Has the team the learner is currently on already submitted?
            team_info['has_submitted'] = self.config_data.does_team_have_submission(team_id)

        if workflow:
            # If the learner has submitted, use the team id on the learner's submission later
            # for shared files lookup. If the learner has submitted already for a different team
            # and then joined another team, we should show the submission that they are actually a part of,
            # rather than just their current team. If they have a submission (and therefore a workflow) then
            # that takes precedence.
            team_submission = get_team_submission(workflow['team_submission_uuid'])
            team_id = team_submission['team_id']
        return team_info, team_id

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
