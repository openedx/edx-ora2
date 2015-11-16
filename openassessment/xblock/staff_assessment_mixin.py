"""
A mixin for staff grading.
"""
import logging

from staff_area_mixin import require_course_staff
from xblock.core import XBlock

from openassessment.assessment.api import staff as staff_api
from openassessment.workflow import api as workflow_api
from openassessment.assessment.errors import (
    StaffAssessmentRequestError, StaffAssessmentInternalError
)

from .data_conversion import create_rubric_dict
from .resolve_dates import DISTANT_FUTURE
from .data_conversion import clean_criterion_feedback, create_submission_dict

logger = logging.getLogger(__name__)


class StaffAssessmentMixin(object):
    """
    This mixin is for all staff-assessment related endpoints.
    """

    def staff_assessment_exists(self, submission_uuid):
        """
        Returns True if there exists a staff assessment for the given uuid. False otherwise.
        """

        return staff_api.get_latest_staff_assessment(submission_uuid) is not None

    @XBlock.json_handler
    @require_course_staff("STUDENT_INFO")
    def staff_assess(self, data, suffix=''):
        """
        Create a staff assessment from a staff submission.
        """
        if 'options_selected' not in data:
            return {'success': False, 'msg': self._(u"Missing options_selected key in request")}

        if 'overall_feedback' not in data:
            return {'success': False, 'msg': self._('Must provide overall feedback in the assessment')}

        if 'criterion_feedback' not in data:
            return {'success': False, 'msg': self._('Must provide feedback for criteria in the assessment')}

        if 'submission_uuid' not in data:
            return {'success': False, 'msg': self._(u"Missing the submission id of the submission being assessed.")}

        try:
            assessment = staff_api.create_assessment(
                data['submission_uuid'],
                self.get_student_item_dict()["student_id"],
                data['options_selected'],
                clean_criterion_feedback(self.rubric_criteria, data['criterion_feedback']),
                data['overall_feedback'],
                create_rubric_dict(self.prompts, self.rubric_criteria_with_labels)
            )
            self.publish_assessment_event("openassessmentblock.staff_assessment", assessment)
            workflow_api.update_from_assessments(assessment["submission_uuid"], {}, force_update_score=True)

        except StaffAssessmentRequestError:
            logger.warning(
                u"An error occurred while submitting a staff assessment "
                u"for the submission {}".format(self.submission_uuid),
                exc_info=True
            )
            msg = self._(u"Your staff assessment could not be submitted.")
            return {'success': False, 'msg': msg}
        except StaffAssessmentInternalError:
            logger.exception(
                u"An error occurred while submitting a staff assessment "
                u"for the submission {}".format(self.submission_uuid),
            )
            msg = self._(u"Your staff assessment could not be submitted.")
            return {'success': False, 'msg': msg}
        else:
            return {'success': True, 'msg': u""}

    @XBlock.handler
    @require_course_staff("STUDENT_INFO")
    def render_staff_assessment(self, data, suffix=''):
        """
        Render the staff assessment for the given student.
        """
        try:
            submission_uuid = data.get("submission_uuid")
            path, context = self.self_path_and_context(submission_uuid)
        except:
            msg = u"Could not retrieve staff assessment for submission {}".format(self.submission_uuid)
            logger.exception(msg)
            return self.render_error(self._(u"An unexpected error occurred."))
        else:
            return self.render_assessment(path, context)

    def staff_path_and_context(self, submission_uuid):
        """
        Retrieve the correct template path and template context for the handler to render.

        Args:
            submission_uuid (str) -
        """
        #TODO: add in the workflow for staff grading instead of assuming it's allowed.
        submission = submission_api.get_submission(self.submission_uuid)

        context = {'allow_latex': self.allow_latex}
        context["rubric_criteria"] = self.rubric_criteria_with_labels
        context["estimated_time"] = "20 minutes"  # TODO: Need to configure this.
        context["self_submission"] = create_submission_dict(submission, self.prompts)

        # Determine if file upload is supported for this XBlock.
        context["allow_file_upload"] = self.allow_file_upload
        context['self_file_url'] = self.get_download_url_from_submission(submission)

        #TODO: Replace with the staff assessment template when it's been built.
        path = 'openassessmentblock/self/oa_self_assessment.html'
        return path, context
