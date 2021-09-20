"""
API endpoints for enhanced staff grader
"""
from openassessment.staffgrader.errors.submission_lock import SubmissionLockContestedError
from openassessment.xblock.staff_area_mixin import require_course_staff
from xblock.core import XBlock
from xblock.exceptions import JsonHandlerError

from openassessment.staffgrader.models.submission_lock import SubmissionGradingLock
from openassessment.staffgrader.serializers.submission_lock import SubmissionLockSerializer

class StaffGraderMixin:
    """
    Actions to interact with submission locks, blocking other staff from grading assignments while
    grading is in progress.
    """

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    def check_submission_lock(self, data, suffix=""):  # pylint: disable=unused-argument
        # Unpack / validate request
        submission_uuid = data.get('submission_id', None)
        if not submission_uuid:
            raise JsonHandlerError(400, "Body must contain a submission_id")

        submission_lock = SubmissionGradingLock.get_submission_lock(submission_uuid)

        if submission_lock:
            return SubmissionLockSerializer(submission_lock).data
        else:
            return {}

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    def claim_submission_lock(self, data, suffix=''):  # pylint: disable=unused-argument
        # Unpack / validate request
        submission_uuid = data.get('submission_id', None)
        if not submission_uuid:
            raise JsonHandlerError(400, "Body must contain a submission_id")
        anonymous_user_id = self.get_anonymous_user_id_from_xmodule_runtime()

        try:
            submission_lock = SubmissionGradingLock.claim_submission_lock(submission_uuid, anonymous_user_id)
            return SubmissionLockSerializer(submission_lock).data
        except SubmissionLockContestedError as err:
            raise JsonHandlerError(403, str(err))

    @XBlock.json_handler
    @require_course_staff("STUDENT_GRADE")
    def delete_submission_lock(self, data, suffix=''):  # pylint: disable=unused-argument
        # Unpack / validate request
        submission_uuid = data.get('submission_id', None)
        if not submission_uuid:
            raise JsonHandlerError(400, "Body must contain a submission_id")
        anonymous_user_id = self.get_anonymous_user_id_from_xmodule_runtime()

        try:
            SubmissionGradingLock.clear_submission_lock(submission_uuid, anonymous_user_id)
            return {}
        except SubmissionLockContestedError as err:
            raise JsonHandlerError(403, str(err))
