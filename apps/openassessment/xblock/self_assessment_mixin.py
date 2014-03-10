import logging
from django.utils.translation import ugettext as _

from xblock.core import XBlock
from openassessment.assessment import self_api


logger = logging.getLogger(__name__)


class SelfAssessmentMixin(object):
    """The Self Assessment Mixin for all Self Assessment Functionality.

    Abstracts all functionality and handlers associated with Self Assessment.
    All Self Assessment API calls should be contained within this Mixin as
    well.

    SelfAssessmentMixin is a Mixin for the OpenAssessmentBlock. Functions in
    the SelfAssessmentMixin call into the OpenAssessmentBlock functions and
    will not work outside of OpenAssessmentBlock.
    """

    @XBlock.handler
    def render_self_assessment(self, data, suffix=''):
    # Retrieve the self-assessment, if there is one

        workflow = self.get_workflow_info()
        if workflow:
            return self._determine_assessment_state(workflow)

        return self.render_assessment('openassessmentblock/self/oa_self_closed.html')

    def _determine_assessment_state(self, workflow):
        context = {}
        try:
            submission, assessment = self_api.get_submission_and_assessment(
                workflow["submission_uuid"]
            )
        except self_api.SelfAssessmentRequestError:
            logger.exception(
                u"Could not retrieve self assessment for submission {}"
                .format(workflow["submission_uuid"])
            )
            return self.render_error(_(u"An unexpected error occurred."))
        if workflow["status"] == "self":
            path = 'openassessmentblock/self/oa_self_assessment.html'
            context = {
                "rubric_criteria": self.rubric_criteria,
                "estimated_time": "20 minutes",  # TODO: Need to configure this.
                "self_submission": submission,
            }
        elif assessment:
            path = 'openassessmentblock/self/oa_self_complete.html'
        else:
            path = 'openassessmentblock/self/oa_self_closed.html'
        return self.render_assessment(path, context)

    @XBlock.json_handler
    def self_assess(self, data, suffix=''):
        """
        Create a self-assessment for a submission.

        Args:
            data (dict): Must have the following keys:
                submission_uuid (string): The unique identifier of the submission being assessed.
                options_selected (dict): Dictionary mapping criterion names to option values.

        Returns:
            Dict with keys "success" (bool) indicating success/failure
            and "msg" (unicode) containing additional information if an error occurs.
        """
        if 'submission_uuid' not in data:
            return {'success': False, 'msg': _(u"Missing submission_uuid key in request")}
        if 'options_selected' not in data:
            return {'success': False, 'msg': _(u"Missing options_selected key in request")}

        try:
            self_api.create_assessment(
                data['submission_uuid'],
                self.get_student_item_dict()['student_id'],
                data['options_selected'],
                {"criteria": self.rubric_criteria}
            )
        except self_api.SelfAssessmentRequestError as ex:
            msg = _(u"Could not create self assessment: {error}").format(error=ex.message)
            return {'success': False, 'msg': msg}
        else:
            return {'success': True, 'msg': u""}
