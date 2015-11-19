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
from .data_conversion import clean_criterion_feedback, create_submission_dict, verify_assessment_parameters

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
    @verify_assessment_parameters
    def staff_assess(self, data, suffix=''):
        """
        Create a staff assessment from a staff submission.
        """
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
            workflow_api.update_from_assessments(assessment["submission_uuid"], {})

        except StaffAssessmentRequestError:
            logger.warning(
                u"An error occurred while submitting a staff assessment "
                u"for the submission {}".format(data['submission_uuid']),
                exc_info=True
            )
            msg = self._(u"Your staff assessment could not be submitted.")
            return {'success': False, 'msg': msg}
        except StaffAssessmentInternalError:
            logger.exception(
                u"An error occurred while submitting a staff assessment "
                u"for the submission {}".format(data['submission_uuid']),
            )
            msg = self._(u"Your staff assessment could not be submitted.")
            return {'success': False, 'msg': msg}
        else:
            return {'success': True, 'msg': u""}
            
    @XBlock.handler
    def render_staff_assessment(self, data, suffix=''):
        """Renders the Staff Assessment HTML section of the XBlock
        Generates the staff assessment HTML for the Open
        Assessment XBlock. See OpenAssessmentBlock.render_assessment() for
        more information on rendering XBlock sections.
        Args:
            data (dict):
        """
        # if "peer-assessment" not in self.assessment_steps:
        #     return Response(u"")

        path, context_dict = self.staff_path_and_context()

        return self.render_assessment(path, context_dict)
        
    def staff_path_and_context(self):
        """
        Retrieve the correct template path and template context for the handler to render.
        """
        # TODO: what is actually necessary here?
        context_dict = {
            "rubric_criteria": self.rubric_criteria_with_labels,
            "allow_latex": self.allow_latex,
        }

        # # Determine if file upload is supported for this XBlock.
        # context["allow_file_upload"] = self.allow_file_upload
        # context['self_file_url'] = self.get_download_url_from_submission(submission)

        path = 'openassessmentblock/staff/oa_staff_complete.html'
        return path, context_dict       
