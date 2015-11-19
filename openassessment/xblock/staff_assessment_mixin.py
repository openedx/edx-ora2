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
        """
        Renders the Staff Assessment HTML section of the XBlock
        Generates the staff assessment HTML for the Open
        Assessment XBlock. See OpenAssessmentBlock.render_assessment() for
        more information on rendering XBlock sections.
        Args:
            data (dict):
        """
        path, context_dict = self.staff_path_and_context()

        return self.render_assessment(path, context_dict)
        
    def staff_path_and_context(self):
        """
        Retrieve the correct template path and template context for the handler to render.
        """
        workflow = self.get_workflow_info()
        status = workflow.get('status')

        if status == 'cancelled':
            path = 'openassessmentblock/staff/oa_staff_cancelled.html'
        elif status == 'done':  # Staff grade exists and all steps completed.
            path = 'openassessmentblock/staff/oa_staff_complete.html'
        elif status == 'waiting':
            # If we are in the 'waiting' workflow, this means that a staff grade cannot exist
            # (because if a staff grade did exist, we would be in 'done' regardless of whether other
            # peers have assessed). Therefore we show that we are waiting on staff to provide a grade.
            path = 'openassessmentblock/staff/oa_staff_incomplete_waiting.html'
        elif status is None:  # not started
            path = 'openassessmentblock/staff/oa_staff_unavailable.html'
        else:  # status is 'self' or 'peer', indicating that the student still has work to do.
            if self.staff_assessment_exists(self.submission_uuid):
                path = 'openassessmentblock/staff/oa_staff_complete_waiting.html'
            else:  # Both student and staff still have work to do, just show "Not Available".
                path = 'openassessmentblock/staff/oa_staff_unavailable.html'

        return path, {}
