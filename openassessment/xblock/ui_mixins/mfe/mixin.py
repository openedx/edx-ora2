"""
Data layer for ORA

XBlock handlers which surface info about an ORA, instead of being tied to views.
"""
from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError

from openassessment.fileupload.exceptions import FileUploadError
from openassessment.assessment.errors import AssessmentError
from openassessment.workflow.errors import AssessmentWorkflowError
from openassessment.xblock.apis.assessments.errors import InvalidStateToAssess
from openassessment.xblock.apis.assessments.peer_assessment_api import peer_assess
from openassessment.xblock.apis.assessments.self_assessment_api import self_assess
from openassessment.xblock.apis.assessments.student_training_api import training_assess
from openassessment.xblock.apis.submissions import submissions_actions
from openassessment.xblock.apis.submissions.errors import (
    AnswerTooLongException,
    DeleteNotAllowed,
    DraftSaveException,
    EmptySubmissionError,
    MultipleSubmissionsException,
    OnlyOneFileAllowedException,
    StudioPreviewException,
    SubmissionValidationException,
    SubmitInternalError,
    UnsupportedFileTypeException
)
from openassessment.xblock.ui_mixins.mfe.assessment_serializers import (
    AssessmentSubmitRequestSerializer,
    MfeAssessmentDataSerializer,
)
from openassessment.xblock.ui_mixins.mfe.constants import error_codes, handler_suffixes
from openassessment.xblock.ui_mixins.mfe.ora_config_serializer import OraBlockInfoSerializer
from openassessment.xblock.ui_mixins.mfe.page_context_serializer import PageDataSerializer
from openassessment.xblock.ui_mixins.mfe.submission_serializers import (
    AddFileRequestSerializer,
    FileUploadCallbackRequestSerializer
)


class OraApiException(JsonHandlerError):
    """
    JsonHandlerError subclass that when thrown results in a response with the
    given HTTP status code, and a body consisting of the given error code and context.
    """
    def __init__(self, status_code, error_code, error_context=''):
        super().__init__(
            status_code,
            {
                'errorCode': error_code,
                'errorContext': error_context
            }
        )


# Map requested ORA app step to workflow step name
MFE_STEP_TO_WORKFLOW_MAPPINGS = {
    "submission": "submission",
    "studentTraining": "training",
    "peer": "peer",
    "self": "self",
    "staff": "staff",
    "done": "done",
}


class MfeMixin:

    @XBlock.json_handler
    def get_block_info(self, data, suffix=""):  # pylint: disable=unused-argument
        block_info = OraBlockInfoSerializer(self)
        return block_info.data

    @XBlock.json_handler
    def get_learner_data(self, data, suffix=""):  # pylint: disable=unused-argument
        """
        Get data for the user / step of the ORA, based on the following modes:

        1) If no step provided, refresh progress but don't return any response.
        2) If step provided, validate that we can get to that step and return the appropriate response
        """
        # Query workflow step here only once to avoid duplicate workflow updates
        current_workflow_step = self.workflow_data.status or "submission"
        requested_step = suffix

        # Validate that any active step is a valid step
        if suffix and suffix not in handler_suffixes.STEP_SUFFIXES:
            raise OraApiException(400, error_codes.INCORRECT_PARAMETERS, f"Invalid step name: {requested_step}")

        serializer_context = {"requested_step": None, "current_workflow_step": current_workflow_step}

        # For the general case, just return refreshed page data, without a response
        if not requested_step:
            return PageDataSerializer(self, context=serializer_context).data

        # Raise error if step is closed
        elif not self.is_step_open(requested_step):
            raise OraApiException(400, error_codes.INACCESSIBLE_STEP, f"Inaccessible step: {requested_step}")

        # Check to see if user can access this workflow step
        requested_workflow_step = MFE_STEP_TO_WORKFLOW_MAPPINGS[requested_step]
        if not self.workflow_data.has_reached_given_step(
            requested_workflow_step,
            current_workflow_step=current_workflow_step
        ):
            raise OraApiException(400, error_codes.INACCESSIBLE_STEP, f"Inaccessible step: {requested_workflow_step}")

        # If they have access to this step, return the associated data
        serializer_context["requested_step"] = requested_step
        return PageDataSerializer(self, context=serializer_context).data

    def is_step_open(self, step_name):
        """
        Determine whether or not the requested step is open

        Return: If the problem is open or not (Bool)
        Raises: OraApiException if the step name is invalid
        """
        step_data = None

        # Users can always view a submission they've previously submitted
        if step_name == "submission" and self.submission_data.has_submitted:
            return True
        # And whether they can get to grades, depends on the workflow being "done"
        elif step_name == "done":
            return self.workflow_data.is_done

        # Otherwise, get the info for the current step to determine access
        if step_name == "submission":
            step_data = self.submission_data
        elif step_name == "studentTraining":
            step_data = self.student_training_data
        elif step_name == "peer":
            step_data = self.peer_assessment_data()
        elif step_name == "self":
            step_data = self.self_assessment_data
        elif step_name == "staff":
            step_data = self.staff_assessment_data
        else:
            raise OraApiException(400, error_codes.UNKNOWN_SUFFIX, error_context=f"Bad step name: {step_name}")

        # Return if the step is currently open
        return not step_data.problem_closed

    def _submission_draft_handler(self, data):
        try:
            student_submission_data = data['response']['textResponses']
            submissions_actions.save_submission_draft(student_submission_data, self.config_data, self.submission_data)
        except KeyError as e:
            raise OraApiException(400, error_codes.INCORRECT_PARAMETERS) from e
        except SubmissionValidationException as exc:
            raise OraApiException(400, error_codes.INVALID_RESPONSE_SHAPE, str(exc)) from exc
        except DraftSaveException as e:
            raise OraApiException(500, error_codes.INTERNAL_EXCEPTION) from e

    def _submission_create_handler(self, data):
        from submissions import api as submission_api
        try:
            text_responses = data["submission"]["textResponses"]
            submissions_actions.submit(text_responses, self.config_data, self.submission_data, self.workflow_data)
        except KeyError as e:
            raise OraApiException(400, error_codes.INCORRECT_PARAMETERS) from e
        except SubmissionValidationException as e:
            raise OraApiException(400, error_codes.INVALID_RESPONSE_SHAPE, str(e)) from e
        except StudioPreviewException as e:
            raise OraApiException(400, error_codes.IN_STUDIO_PREVIEW) from e
        except MultipleSubmissionsException as e:
            raise OraApiException(400, error_codes.MULTIPLE_SUBMISSIONS) from e
        except AnswerTooLongException as e:
            raise OraApiException(400, error_codes.SUBMISSION_TOO_LONG, {
                'maxsize': submission_api.Submission.MAXSIZE
            }) from e
        except submission_api.SubmissionRequestError as e:
            raise OraApiException(400, error_codes.SUBMISSION_API_ERROR, str(e)) from e
        except EmptySubmissionError as e:
            raise OraApiException(400, error_codes.EMPTY_ANSWER) from e
        except SubmitInternalError as e:
            raise OraApiException(500, error_codes.UNKNOWN_ERROR, str(e)) from e

    @XBlock.json_handler
    def submission(self, data, suffix=""):
        if suffix == handler_suffixes.SUBMISSION_DRAFT:
            return self._submission_draft_handler(data)
        elif suffix == handler_suffixes.SUBMISSION_SUBMIT:
            # Return an error if the submission step is not open
            if not self.is_step_open("submission"):
                raise OraApiException(400, error_codes.INACCESSIBLE_STEP)
            return self._submission_create_handler(data)
        else:
            raise OraApiException(404, error_codes.UNKNOWN_SUFFIX)

    def _file_delete_handler(self, data):
        try:
            file_index = int(data['fileIndex'])
        except (KeyError, ValueError) as e:
            raise OraApiException(400, error_codes.INCORRECT_PARAMETERS) from e
        try:
            submissions_actions.remove_uploaded_file(
                file_index,
                self.config_data,
                self.submission_data,
            )
        except DeleteNotAllowed as e:
            raise OraApiException(400, error_codes.DELETE_NOT_ALLOWED) from e
        except FileUploadError as e:
            raise OraApiException(500, error_codes.INTERNAL_EXCEPTION, str(e)) from e

    def _get_new_file_from_list(self, file_to_add, new_list):
        for file_entry in new_list:
            if all((
                file_entry.name == file_to_add['name'],
                file_entry.description == file_to_add['description'],
                file_entry.size == file_to_add['size']
            )):
                return file_entry
        return None

    def _file_add_handler(self, data):
        serializer = AddFileRequestSerializer(data=data)
        if not serializer.is_valid():
            raise OraApiException(400, error_codes.INCORRECT_PARAMETERS, serializer.errors)
        file_to_add = serializer.validated_data
        try:
            new_files = submissions_actions.append_file_data(
                [file_to_add],
                self.config_data,
                self.submission_data,
            )
        except FileUploadError as e:
            raise OraApiException(500, error_codes.INTERNAL_EXCEPTION, str(e)) from e

        newly_added_file = self._get_new_file_from_list(file_to_add, new_files)
        if newly_added_file is None:
            raise OraApiException(500, error_codes.INTERNAL_EXCEPTION)

        try:
            try:
                url = submissions_actions.get_upload_url(
                    file_to_add['contentType'],
                    newly_added_file.name,
                    newly_added_file.index,
                    self.config_data,
                    self.submission_data,
                )
                if url is None:
                    raise OraApiException(500, error_codes.UNABLE_TO_GENERATE_UPLOAD_URL)
            except OnlyOneFileAllowedException as e:
                raise OraApiException(400, error_codes.TOO_MANY_UPLOADS) from e
            except UnsupportedFileTypeException as e:
                raise OraApiException(400, error_codes.UNSUPPORTED_FILETYPE, str(e)) from e
            except FileUploadError as e:
                raise OraApiException(500, error_codes.UNABLE_TO_GENERATE_UPLOAD_URL, str(e)) from e
        except OraApiException:
            # If we've raised an OraApiException for any reason, remove the bad file from the user metadata
            self.submission_data.files.delete_uploaded_file(newly_added_file.index)
            raise

        return {
            'fileUrl': url,
            'fileIndex': newly_added_file.index,
        }

    def _file_upload_callback_handler(self, data):
        serializer = FileUploadCallbackRequestSerializer(data=data)
        if not serializer.is_valid():
            raise OraApiException(400, error_codes.INCORRECT_PARAMETERS, serializer.errors)
        fileIndex = serializer.validated_data['fileIndex']

        if not serializer.validated_data['success']:
            self.submission_data.files.delete_uploaded_file(fileIndex)
            return None

        url = self.submission_data.files.get_download_url(fileIndex)
        if url is None:
            self.submission_data.files.delete_uploaded_file(fileIndex)
            raise OraApiException(404, error_codes.FILE_NOT_FOUND)
        return {'downloadUrl': url}

    @XBlock.json_handler
    def file(self, data, suffix=""):
        if suffix == handler_suffixes.FILE_DELETE:
            return self._file_delete_handler(data)
        elif suffix == handler_suffixes.FILE_ADD:
            return self._file_add_handler(data)
        elif suffix == handler_suffixes.FILE_UPLOAD_CALLBACK:
            return self._file_upload_callback_handler(data)
        else:
            raise OraApiException(404, error_codes.UNKNOWN_SUFFIX)

    def _get_in_progress_file_upload_data(self, team_id=None):
        if not self.file_upload_type:
            return []
        return self.file_manager.file_descriptors(team_id=team_id, include_deleted=True)

    def _get_in_progress_team_file_upload_data(self, team_id=None):
        if not self.file_upload_type or not self.is_team_assignment():
            return []
        return self.submission_data.files.file_manager.team_file_descriptors(team_id=team_id)

    def get_learner_submission_data(self):
        # TODO - Move this out of mixin, this is only here because it accesses
        # private functions in the mixin but should actually be in SubmissionAPI

        # Get team / individual workflow
        workflow = None
        if self.is_team_assignment():
            workflow = self.get_team_workflow_info()
        else:
            workflow = self.workflow_data.get_workflow_info()

        team_info, team_id = self.submission_data.get_submission_team_info(workflow)

        # If there is a submission, we do not need to load file upload data separately because files
        # will already have been gathered into the submission. If there is no submission, we need to
        # load file data from learner state and the SharedUpload db model
        if self.submission_data.has_submitted:
            response = self.submission_data.get_submission(
                self.submission_data.workflow['submission_uuid']
            )
            file_data = []
        else:
            response = self.submission_data.saved_response_submission_dict
            file_data = self._get_in_progress_file_upload_data(team_id)
            team_info['team_uploaded_files'] = self._get_in_progress_team_file_upload_data(team_id)

        return {
            'workflow': {
                'has_submitted': self.submission_data.has_submitted,
                'has_cancelled': self.workflow_data.is_cancelled,
                'has_received_grade': self.workflow_data.has_received_grade,
            },
            'team_info': team_info,
            'response': response,
            'file_data': file_data,
        }

    def _assessment_submit_handler(self, data):
        serializer = AssessmentSubmitRequestSerializer(data=data)
        if not serializer.is_valid():
            raise OraApiException(400, error_codes.INCORRECT_PARAMETERS, serializer.errors)
        assessment_data = serializer.to_legacy_format(self)
        requested_step = serializer.data['step']
        try:
            # Block assessing a closed step
            if not self.is_step_open(requested_step):
                raise OraApiException(400, error_codes.INACCESSIBLE_STEP, f"Inaccessible step: {requested_step}")

            # Block assessing a cancelled submission
            if self.workflow_data.is_cancelled:
                raise InvalidStateToAssess()

            if requested_step == 'peer':
                peer_assess(
                    assessment_data['options_selected'],
                    assessment_data['feedback'],
                    assessment_data['criterion_feedback'],
                    self.config_data,
                    self.workflow_data,
                    self.peer_assessment_data(),
                )
            elif requested_step == 'self':
                self_assess(
                    assessment_data['options_selected'],
                    assessment_data['criterion_feedback'],
                    assessment_data['feedback'],
                    self.config_data,
                    self.workflow_data,
                    self.self_assessment_data
                )
            elif requested_step == 'studentTraining':
                corrections = training_assess(
                    assessment_data['options_selected'],
                    self.config_data,
                    self.workflow_data,
                )
                if corrections:
                    raise OraApiException(400, error_codes.TRAINING_ANSWER_INCORRECT, corrections)
            else:
                raise InvalidStateToAssess()
        except InvalidStateToAssess as e:
            # This catches the error we explicitly raise, as well as any that may be raised from within
            # the assessment logic itself
            context = {
                'requested_step': requested_step,
                'student_item': self.config_data.student_item_dict,
                'workflow': self.workflow_data.workflow,
            }
            raise OraApiException(400, error_codes.INVALID_STATE_TO_ASSESS, context) from e
        except (AssessmentError, AssessmentWorkflowError) as e:
            raise OraApiException(500, error_codes.INTERNAL_EXCEPTION, str(e)) from e

        # Return assessment data for the frontend
        return MfeAssessmentDataSerializer(data).data

    @XBlock.json_handler
    def assessment(self, data, suffix=""):
        if suffix == handler_suffixes.ASSESSMENT_SUBMIT:
            return self._assessment_submit_handler(data)
        else:
            raise OraApiException(404, error_codes.UNKNOWN_SUFFIX)
