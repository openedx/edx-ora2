"""
Data layer for ORA

XBlock handlers which surface info about an ORA, instead of being tied to views.
"""
from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError
from openassessment.fileupload.exceptions import FileUploadError

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
from openassessment.xblock.ui_mixins.mfe.constants import error_codes, handler_suffixes
from openassessment.xblock.ui_mixins.mfe.ora_config_serializer import OraBlockInfoSerializer
from openassessment.xblock.ui_mixins.mfe.page_context_serializer import PageDataSerializer
from openassessment.xblock.ui_mixins.mfe.submission_serializers import AddFileRequestSerializer


class OraApiException(JsonHandlerError):
    """
    JsonHandlerError subclass that when thrown results in a response with the
    given HTTP status code, and a body consisting of the given error code and context.
    """
    def __init__(self, status_code, error_code, error_context=''):
        super().__init__(
            status_code,
            {
                'error_code': error_code,
                'error_context': error_context
            }
        )


class MfeMixin:
    @XBlock.json_handler
    def get_block_info(self, data, suffix=""):  # pylint: disable=unused-argument
        block_info = OraBlockInfoSerializer(self)
        return block_info.data

    @XBlock.json_handler
    def get_block_learner_submission_data(self, data, suffix=""):  # pylint: disable=unused-argument
        serializer_context = {"view": "submission"}
        page_context = PageDataSerializer(self, context=serializer_context)
        return page_context.data

    @XBlock.json_handler
    def get_block_learner_assessment_data(self, data, suffix=""):  # pylint: disable=unused-argument
        serializer_context = {"view": "assessment", "step": suffix}

        # Allow jumping to a specific step, within our allowed steps
        # NOTE should probably also verify this step is in our assessment steps
        # though the serializer also covers for this currently
        jumpable_steps = "peer"
        if suffix in jumpable_steps:
            serializer_context.update({"jump_to_step": suffix})

        page_context = PageDataSerializer(self, context=serializer_context)
        return page_context.data

    def _submission_draft_handler(self, data):
        try:
            student_submission_data = data['response']['text_responses']
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
            submissions_actions.submit(data, self.config_data, self.submission_data, self.workflow_data)
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

    @XBlock.json_handler
    def file(self, data, suffix=""):
        if suffix == handler_suffixes.FILE_DELETE:
            return self._file_delete_handler(data)
        elif suffix == handler_suffixes.FILE_ADD:
            return self._file_add_handler(data)
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
        workflow = self.get_team_workflow_info() if self.is_team_assignment() else self.get_workflow_info()
        team_info, team_id = self.submission_data.get_submission_team_info(workflow)
        # If there is a submission, we do not need to load file upload data seprately because files
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
                'has_recieved_grade': self.workflow_data.has_recieved_grade,
            },
            'team_info': team_info,
            'response': response,
            'file_data': file_data,
        }
