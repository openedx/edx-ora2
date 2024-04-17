"""JSON handlers for the old-style ORA UI"""

import logging

from xblock.core import XBlock
from submissions import api as submissions_api
from openassessment.assessment.errors.peer import (
    PeerAssessmentInternalError,
    PeerAssessmentRequestError,
    PeerAssessmentWorkflowError,
)
from openassessment.assessment.errors.self import SelfAssessmentInternalError, SelfAssessmentRequestError
from openassessment.assessment.errors.staff import StaffAssessmentInternalError, StaffAssessmentRequestError
from openassessment.assessment.errors.student_training import StudentTrainingError
from openassessment.fileupload.exceptions import FileUploadError
from openassessment.workflow.errors import (
    AssessmentWorkflowError,
    AssessmentWorkflowInternalError,
    AssessmentWorkflowRequestError
)
from openassessment.xblock.apis.assessments.errors import (
    ReviewerMustHaveSubmittedException,
    ServerClientUUIDMismatchException,
)
from openassessment.xblock.apis.submissions import submissions_actions
from openassessment.xblock.apis.assessments.peer_assessment_api import peer_assess
from openassessment.xblock.apis.assessments.self_assessment_api import self_assess
from openassessment.xblock.apis.assessments.staff_assessment_api import staff_assess
from openassessment.xblock.apis.assessments.student_training_api import training_assess
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
from openassessment.xblock.staff_area_mixin import require_course_staff
from openassessment.xblock.ui_mixins.legacy.serializers import SaveFilesDescriptionRequestSerializer
from openassessment.xblock.utils.data_conversion import verify_assessment_parameters

logger = logging.getLogger(__name__)


def _safe_read_file_index(data, default):
    """ Helper for remove_uploaded_file handler """
    file_index = data.get("filenum", default)
    try:
        file_index = int(file_index)
    except ValueError:
        file_index = default
    return file_index


class LegacyHandlersMixin:
    """
    Exposes actions (@XBlock.json_handlers) used in our legacy ORA UI
    """

    # Submissions

    @XBlock.json_handler
    def submit(self, data, suffix=""):  # pylint: disable=unused-argument
        """Submit a response for the student provided in data['submission']"""
        if "submission" not in data:
            return (
                False,
                "EBADARGS",
                self.config_data.translate('"submission" required to submit answer.'),
            )
        try:
            submission = submissions_actions.submit(
                data["submission"],
                self.config_data,
                self.submission_data,
                self.workflow_data
            )
            return (
                True,
                submission.get("student_item"),
                submission.get("attempt_number")
            )
        except SubmissionValidationException as e:
            return False, 'EBADARGS', str(e)
        except StudioPreviewException:
            status_text = self.config_data.translate(
                'To submit a response, view this component in Preview or Live mode.'
            )
            return False, 'ENOPREVIEW', status_text
        except MultipleSubmissionsException:
            status_text = self.config_data.translate('Multiple submissions are not allowed.')
            return False, 'ENOMULTI', status_text
        except AnswerTooLongException:
            max_size = f"({int(submissions_api.Submission.MAXSIZE / 1024)} KB)"
            base_error = self.config_data.translate("Response exceeds maximum allowed size.")
            extra_info = self.config_data.translate(
                "Note: if you have a spellcheck or grammar check browser extension, "
                "try disabling, reloading, and reentering your response before submitting."
            )
            status_text = f"{base_error} {max_size} {extra_info}"
            return False, 'EANSWERLENGTH', status_text
        except submissions_api.SubmissionRequestError:
            status_text = self.config_data.translate(
                'The submissions API reported an invalid request error '
                'when submitting a response'
            )
            return False, 'EBADFORM', status_text
        except EmptySubmissionError:
            status_text = self.config_data.translate(
                'Submission cannot be empty. '
                'Please refresh the page and try again.'
            )
            return False, 'EEMPTYSUB', status_text
        except SubmitInternalError:
            status_text = self.config_data.translate('API returned unclassified exception.')
            return False, 'EUNKNOWN', status_text

    @XBlock.json_handler
    def save_submission(self, data, suffix=""):  # pylint: disable=unused-argument
        """Save a draft response for the student under data['submission']"""
        if 'submission' not in data:
            return {
                'success': False,
                'msg': self.config_data.translate("Submission data missing. Please contact support staff.")
            }
        student_submission_data = data['submission']
        try:
            submissions_actions.save_submission_draft(student_submission_data, self.config_data, self.submission_data)
        except SubmissionValidationException as exc:
            return {'success': False, 'msg': str(exc)}
        except DraftSaveException:
            return {'success': False, 'msg': self.config_data.translate("Please contact support staff.")}
        else:
            return {'success': True, 'msg': ''}

    # File uploads
    @XBlock.json_handler
    def save_files_descriptions(self, data, suffix=""):  # pylint: disable=unused-argument
        serializer = SaveFilesDescriptionRequestSerializer(data=data)
        if not serializer.is_valid():
            return {
                'success': False,
                'msg': self.config_data.translate('File descriptions were not submitted.'),
            }

        try:
            submissions_actions.append_file_data(
                serializer.validated_data['fileMetadata'],
                self.config_data,
                self.submission_data,
            )
        except FileUploadError:
            return {
                'success': False,
                'msg': self.config_data.translate("Files metadata could not be saved.")
            }
        else:
            return {'success': True, 'msg': ''}

    @XBlock.json_handler
    def upload_url(self, data, suffix=""):  # pylint: disable=unused-argument
        if "contentType" not in data or "filename" not in data:
            return {
                "success": False,
                "msg": self.config_data.translate("There was an error uploading your file."),
            }
        file_index = _safe_read_file_index(data, 0)
        try:
            url = submissions_actions.get_upload_url(
                data['contentType'],
                data['filename'],
                file_index,
                self.config_data,
                self.submission_data,
            )
        except OnlyOneFileAllowedException:
            return {
                "success": False,
                "msg": self.config_data.translate("Only a single file upload is allowed for this assessment."),
            }
        except UnsupportedFileTypeException:
            return {
                "success": False,
                "msg": self.config_data.translate(
                    "File upload failed: unsupported file type."
                    "Only the supported file types can be uploaded."
                    "If you have questions, please reach out to the course team."
                ),
            }

        except FileUploadError:
            return {
                "success": False,
                "msg": self.config_data.translate("Error retrieving upload URL."),
            }
        else:
            return {'success': True, 'url': url}

    @XBlock.json_handler
    def download_url(self, data, suffix=""):  # pylint: disable=unused-argument
        file_index = _safe_read_file_index(data, 0)
        file_url = self.submission_data.files.get_download_url(file_index)
        return {"success": True, "url": file_url}

    @XBlock.json_handler
    def remove_uploaded_file(self, data, suffix=""):  # pylint: disable=unused-argument
        file_index = _safe_read_file_index(data, -1)
        try:
            submissions_actions.remove_uploaded_file(file_index, self.config_data, self.submission_data, )
        except (FileUploadError, DeleteNotAllowed):
            return {'success': False}
        else:
            return {'success': True}

    # Assessments
    @XBlock.json_handler
    @verify_assessment_parameters
    def peer_assess(self, data, suffix=""):  # pylint: disable=unused-argument
        """Place a peer assessment into OpenAssessment system

        Assess a Peer Submission.  Performs basic workflow validation to ensure
        that an assessment can be performed as this time.

        Args:
            data (dict): A dictionary containing information required to create
                a new peer assessment.  This dict should have the following attributes:
                `submission_uuid` (string): The unique identifier for the submission being assessed.
                `options_selected` (dict): Dictionary mapping criterion names to option values.
                `overall_feedback` (unicode): Written feedback for the submission as a whole.
                `criterion_feedback` (unicode): Written feedback per the criteria for the submission.

        Returns:
            Dict with keys "success" (bool) indicating success/failure.
            and "msg" (unicode) containing additional information if an error occurs.
        """
        try:
            peer_assess(
                data['options_selected'],
                data['overall_feedback'],
                data['criterion_feedback'],
                self.config_data,
                self.workflow_data,
                self.peer_assessment_data(),
                assessed_submission_uuid=data['submission_uuid'],
            )
        except ReviewerMustHaveSubmittedException:
            return {
                'success': False,
                'msg': self.config_data.translate(
                    'You must submit a response before you can perform a peer assessment.'
                )
            }
        except ServerClientUUIDMismatchException:
            return {
                'success': False,
                'msg': self.config_data.translate(
                    'This feedback has already been submitted or the submission has been cancelled.'
                )
            }
        except (PeerAssessmentRequestError, PeerAssessmentWorkflowError, PeerAssessmentInternalError):
            return {
                'success': False,
                'msg': self.config_data.translate('Your peer assessment could not be submitted.')
            }
        except AssessmentWorkflowError:
            return {'success': False, 'msg': self.config_data.translate('Could not update workflow status.')}
        else:
            return {"success": True, "msg": ""}

    @XBlock.json_handler
    @verify_assessment_parameters
    def self_assess(self, data, suffix=""):  # pylint: disable=unused-argument
        """
        Create a self-assessment for a submission.

        Args:
            data (dict): Must have the following keys:
                options_selected (dict): Dictionary mapping criterion names to option values.

        Returns:
            Dict with keys "success" (bool) indicating success/failure
            and "msg" (unicode) containing additional information if an error occurs.
        """
        def failure_response(reason):
            return {'success': False, 'msg': self.config_data.translate(reason)}

        try:
            self_assess(
                data['options_selected'],
                data['criterion_feedback'],
                data['overall_feedback'],
                self.config_data,
                self.workflow_data,
                self.self_assessment_data,
            )
        except ReviewerMustHaveSubmittedException:
            return failure_response('You must submit a response before you can perform a self-assessment.')
        except (
            SelfAssessmentRequestError,
            AssessmentWorkflowRequestError,
            SelfAssessmentInternalError,
            AssessmentWorkflowInternalError
        ):
            return failure_response('Your self assessment could not be submitted.')
        else:
            return {'success': True, 'msg': ''}

    @XBlock.json_handler
    def training_assess(self, data, suffix=""):  # pylint: disable=unused-argument
        """
        Compare the scores given by the student with those given by the course author.
        If they match, update the training workflow.  The client can then reload this
        step to view the next essay or the completed step.

        Currently, we return a boolean indicating whether the student assessed correctly
        or not.  However, the student training API provides the exact criteria that the student
        scored incorrectly, as well as the "correct" options for those criteria.
        In the future, we may expose this in the UI to provide more detailed feedback.

        Args:
            data (dict): Must have the following keys:
                options_selected (dict): Dictionary mapping criterion names to option values.

        Returns:
            Dict with keys:
                * "success" (bool) indicating success or error
                * "msg" (unicode) containing additional information if an error occurs.
                * "correct" (bool) indicating whether the student scored the assessment correctly.

        """
        def failure_response(message):
            return {"success": False, "msg": self.config_data.translate(message)}

        if "options_selected" not in data:
            return failure_response("Missing options_selected key in request.")
        if not isinstance(data["options_selected"], dict):
            return failure_response("options_selected must be a dictionary.")

        try:
            corrections = training_assess(data['options_selected'], self.config_data, self.workflow_data)
        except StudentTrainingError:
            return failure_response("Your scores could not be checked.")
        except AssessmentWorkflowError:
            return failure_response("Could not update workflow status.")
        except Exception:  # pylint: disable=broad-except
            return failure_response("An unexpected error occurred.")

        return {
            "success": True,
            "msg": "",
            "corrections": corrections,
        }

    @XBlock.json_handler
    @require_course_staff("STUDENT_INFO")
    @verify_assessment_parameters
    def staff_assess(self, data, suffix=""):  # pylint: disable=unused-argument
        """
        Create a staff assessment for a team or individual submission.
        """
        def failure_response(reason):
            return {'success': False, 'msg': self.config_data.translate(reason)}

        if 'submission_uuid' not in data:
            return failure_response('The submission ID of the submission being assessed was not found.')

        try:
            staff_assess(
                data['submission_uuid'],
                data['options_selected'],
                data['criterion_feedback'],
                data['overall_feedback'],
                data.get('assess_type', 'regrade'),
                self.config_data,
                self.staff_assessment_data,
            )
        except (StaffAssessmentRequestError, StaffAssessmentInternalError):
            return failure_response('Your team assessment could not be submitted.')
        return {'success': True, 'msg': ''}

    # Utils

    @XBlock.json_handler
    def get_student_username(self, data, suffix=""):  # pylint: disable=unused-argument
        """
        Gets the username of the current student for use in team lookup.
        """
        anonymous_id = self.xmodule_runtime.anonymous_student_id
        return {"username": self.get_username(anonymous_id)}
