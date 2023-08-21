"""
A mixin for staff grading.
"""


import logging

from xblock.core import XBlock

from openassessment.assessment.api import (
    staff as staff_api,
)
from openassessment.assessment.errors import StaffAssessmentInternalError, StaffAssessmentRequestError
from openassessment.workflow import (
    api as workflow_api,
    team_api as team_workflow_api
)

from .data_conversion import (
    verify_assessment_parameters,
)
from .staff_area_mixin import require_course_staff

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class StaffAssessmentMixin:
    """
    This mixin is for all staff-assessment related endpoints.
    """

    def staff_assessment_exists(self, submission_uuid):
        """
        Returns True if there exists a staff assessment for the given uuid. False otherwise.
        """

        return staff_api.get_latest_staff_assessment(submission_uuid) is not None

    def do_staff_assessment(self, data):
        """
        Create a staff assessment from a staff submission.
        """
        if 'submission_uuid' not in data:
            return False, self._("The submission ID of the submission being assessed was not found.")
        try:
            assessment = self.staff_data.create_assessment(data)
            assess_type = data.get('assess_type', 'regrade')
            self.publish_assessment_event("openassessmentblock.staff_assess", assessment, type=assess_type)
            workflow_api.update_from_assessments(
                assessment["submission_uuid"],
                None,
                {},
                override_submitter_requirements=(assess_type == 'regrade')
            )
        except StaffAssessmentRequestError:
            logger.warning(
                "An error occurred while submitting a staff assessment "
                "for the submission %s",
                data['submission_uuid'],
                exc_info=True
            )
            msg = self._("Your staff assessment could not be submitted.")
            return False, msg
        except StaffAssessmentInternalError:
            logger.exception(
                "An error occurred while submitting a staff assessment "
                "for the submission %s",
                data['submission_uuid']
            )
            msg = self._("Your staff assessment could not be submitted.")
            return False, msg
        return True, ''

    def do_team_staff_assessment(self, data, team_submission_uuid=None):
        """
        Teams version of do_staff_assessment.
        Providing the team_submission_uuid removes lookup of team submission from individual submission_uuid.
        """
        if 'submission_uuid' not in data and team_submission_uuid is None:
            return False, self._("The submission ID of the submission being assessed was not found.")
        try:
            assessment, team_submission_uuid = self.staff_data.create_team_assessment(data)
            assess_type = data.get('assess_type', 'regrade')
            self.publish_assessment_event("openassessmentblock.staff_assess", assessment[0], type=assess_type)
            team_workflow_api.update_from_assessments(
                team_submission_uuid,
                override_submitter_requirements=(assess_type == 'regrade')
            )

        except StaffAssessmentRequestError:
            logger.warning(
                "An error occurred while submitting a team assessment "
                "for the submission %s",
                data['submission_uuid'],
                exc_info=True
            )
            msg = self._("Your team assessment could not be submitted.")
            return False, msg
        except StaffAssessmentInternalError:
            logger.exception(
                "An error occurred while submitting a team assessment "
                "for the submission %s",
                data['submission_uuid'],
            )
            msg = self._("Your team assessment could not be submitted.")
            return False, msg

        return True, ''

    @XBlock.json_handler
    @require_course_staff("STUDENT_INFO")
    @verify_assessment_parameters
    def staff_assess(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Create a staff assessment from a team or individual submission.
        """
        if self.is_team_assignment():
            success, err_msg = self.do_team_staff_assessment(data)
        else:
            success, err_msg = self.do_staff_assessment(data)

        return {'success': success, 'msg': err_msg}

    @XBlock.handler
    def render_staff_assessment(self, data, suffix=''):  # pylint: disable=unused-argument
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

    def staff_context(self):
        """
        Retrieve the correct template path and template context for the handler to render.
        """
        step_data = self.staff_data

        not_available_context = {
            'status_value': self._('Not Available'),
            'button_active': 'disabled=disabled aria-expanded=false',
            'step_classes': 'is--unavailable',
        }

        if step_data.is_cancelled:
            context = {
                'status_value': self._('Cancelled'),
                'icon_class': 'fa-exclamation-triangle',
                'step_classes': 'is--unavailable',
                'button_active': 'disabled=disabled aria-expanded=false',
            }
        elif step_data.is_done:  # Staff grade exists and all steps completed.
            context = {
                'status_value': self._('Complete'),
                'icon_class': 'fa-check',
                'step_classes': 'is--complete is--empty',
                'button_active': 'disabled=disabled aria-expanded=false',
            }
        elif step_data.is_waiting:
            # If we are in the 'waiting' workflow, this means that a staff grade cannot exist
            # (because if a staff grade did exist, we would be in 'done' regardless of whether other
            # peers have assessed). Therefore we show that we are waiting on staff to provide a grade.
            context = {
                'status_value': self._('Not Available'),
                'message_title': self._('Waiting for a Staff Grade'),
                'message_content': self._('Check back later to see if a course staff member has assessed '
                                          'your response. You will receive your grade after the assessment '
                                          'is complete.'),
                'step_classes': 'is--showing',
                'button_active': 'aria-expanded=true',
            }
        elif not step_data.has_status:
            context = not_available_context
        else:  # status is 'self' or 'peer', indicating that the student still has work to do.
            if self.staff_assessment_exists(self.submission_uuid):
                context = {
                    'status_value': self._('Complete'),
                    'icon_class': 'fa-check',
                    'message_title': self._('You Must Complete the Steps Above to View Your Grade'),
                    'message_content': self._('Although a course staff member has assessed your response, '
                                              'you will receive your grade only after you have completed '
                                              'all the required steps of this problem.'),
                    'step_classes': 'is--initially--collapsed',
                    'button_active': 'aria-expanded=false',
                }
            else:  # Both student and staff still have work to do, just show "Not Available".
                context = not_available_context

        context['xblock_id'] = self.get_xblock_id()
        return context


    def staff_path_and_context(self):
        """
        Retrieve the correct template path and template context for the handler to render.
        """
        return 'openassessmentblock/staff/oa_staff_grade.html', self.staff_context()
