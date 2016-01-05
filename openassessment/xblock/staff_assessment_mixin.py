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
from .data_conversion import clean_criterion_feedback, verify_assessment_parameters

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
            return {
                'success': False, 'msg': self._(u"The submission ID of the submission being assessed was not found.")
            }

        try:
            assessment = staff_api.create_assessment(
                data['submission_uuid'],
                self.get_student_item_dict()["student_id"],
                data['options_selected'],
                clean_criterion_feedback(self.rubric_criteria, data['criterion_feedback']),
                data['overall_feedback'],
                create_rubric_dict(self.prompts, self.rubric_criteria_with_labels)
            )
            assess_type = data.get('assess_type', 'regrade')
            self.publish_assessment_event("openassessmentblock.staff_assess", assessment, type=assess_type)
            workflow_api.update_from_assessments(assessment["submission_uuid"], None)

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
        path = 'openassessmentblock/staff/oa_staff_grade.html'
        not_available_context = {
            'status_value': self._('Not Available'),
            'step_classes': 'is--unavailable is--empty is--collapsed',
        }

        if status == 'cancelled':
            context = {
                'status_value': self._('Cancelled'),
                'icon_class': 'fa-exclamation-triangle',
            }
        elif status == 'done':  # Staff grade exists and all steps completed.
            context = {
                'status_value': self._('Complete'),
                'icon_class': 'fa-check',
                'step_classes': 'is--complete is--empty is--collapsed',
            }
        elif status == 'waiting':
            # If we are in the 'waiting' workflow, this means that a staff grade cannot exist
            # (because if a staff grade did exist, we would be in 'done' regardless of whether other
            # peers have assessed). Therefore we show that we are waiting on staff to provide a grade.
            context = {
                'status_value': self._('Not Available'),
                'message_title': self._('Waiting for a Staff Grade'),
                'message_content': self._('Check back later to see if a course staff member has assessed your response. You will receive your grade after the assessment is complete.'),
            }
        elif status is None:  # not started
            context = not_available_context
        else:  # status is 'self' or 'peer', indicating that the student still has work to do.
            if self.staff_assessment_exists(self.submission_uuid):
                context = {
                    'status_value': self._('Complete'),
                    'icon_class': 'fa-check',
                    'message_title': self._('You Must Complete the Steps Above to View Your Grade'),
                    'message_content': self._('Although a course staff member has assessed your response, you will receive your grade only after you have completed all the required steps of this problem.'),
                }
            else:  # Both student and staff still have work to do, just show "Not Available".
                context = not_available_context

        return path, context
