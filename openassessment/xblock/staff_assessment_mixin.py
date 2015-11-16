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
            workflow_api.update_from_assessments(assessment["submission_uuid"], {}, force_update_score=True)

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
