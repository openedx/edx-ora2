import logging
from django.utils.translation import ugettext as _

from xblock.core import XBlock
from openassessment.assessment import self_api
from openassessment.workflow import api as workflow_api
from submissions import api as submission_api
from .resolve_dates import DISTANT_FUTURE

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
        try:
            path, context = self.self_path_and_context()
        except:
            msg = u"Could not retrieve self assessment for submission {}".format(self.submission_uuid)
            logger.exception(msg)
            return self.render_error(_(u"An unexpected error occurred."))
        else:
            return self.render_assessment(path, context)

    def self_path_and_context(self):
        """
        Determine the template path and context to use when rendering the self-assessment step.

        Returns:
            tuple of `(path, context)`, where `path` (str) is the path to the template,
            and `context` (dict) is the template context.

        Raises:
            SubmissionError: Error occurred while retrieving the current submission.
            SelfAssessmentRequestError: Error occurred while checking if we had a self-assessment.
        """
        context = {}
        path = 'openassessmentblock/self/oa_self_unavailable.html'
        problem_closed, reason, start_date, due_date = self.is_closed(step="self-assessment")

        # We display the due date whether the problem is open or closed.
        # If no date is set, it defaults to the distant future, in which
        # case we don't display the date.
        if due_date < DISTANT_FUTURE:
            context['self_due'] = due_date

        # If we haven't submitted yet, `workflow` will be an empty dict,
        # and `workflow_status` will be None.
        workflow = self.get_workflow_info()
        workflow_status = workflow.get('status')

        if workflow_status == 'waiting' or workflow_status == 'done':
            path = 'openassessmentblock/self/oa_self_complete.html'
        elif workflow_status == 'self' or problem_closed:
            assessment = self_api.get_assessment(workflow.get("submission_uuid"))

            if assessment is not None:
                path = 'openassessmentblock/self/oa_self_complete.html'
            elif problem_closed:
                if reason == 'start':
                    context["self_start"] = start_date
                    path = 'openassessmentblock/self/oa_self_unavailable.html'
                elif reason == 'due':
                    path = 'openassessmentblock/self/oa_self_closed.html'
            else:
                submission = submission_api.get_submission(self.submission_uuid)
                context["rubric_criteria"] = self.rubric_criteria
                context["estimated_time"] = "20 minutes"  # TODO: Need to configure this.
                context["self_submission"] = submission
                path = 'openassessmentblock/self/oa_self_assessment.html'
        else:
            # No submission yet or in peer assessment
            path = 'openassessmentblock/self/oa_self_unavailable.html'

        return path, context

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
        if 'options_selected' not in data:
            return {'success': False, 'msg': _(u"Missing options_selected key in request")}

        try:
            assessment = self_api.create_assessment(
                self.submission_uuid,
                self.get_student_item_dict()['student_id'],
                data['options_selected'],
                {"criteria": self.rubric_criteria}
            )
            self.runtime.publish(
                self,
                "openassessmentblock.self_assess",
                {
                    "feedback": assessment["feedback"],
                    "rubric": {
                        "content_hash": assessment["rubric"]["content_hash"],
                    },
                    "scorer_id": assessment["scorer_id"],
                    "score_type": assessment["score_type"],
                    "scored_at": assessment["scored_at"],
                    "submission_uuid": assessment["submission_uuid"],
                    "parts": [
                        {
                            "option": {
                                "name": part["option"]["name"],
                                "points": part["option"]["points"]
                            }
                        }
                        for part in assessment["parts"]
                    ]
                }
            )
            # After we've created the self-assessment, we need to update the workflow.
            self.update_workflow_status()
        except self_api.SelfAssessmentRequestError as ex:
            msg = _(u"Could not create self assessment: {error}").format(error=ex.message)
            return {'success': False, 'msg': msg}
        except workflow_api.AssessmentWorkflowError as ex:
            msg = _(u"Could not update workflow: {error}").format(error=ex.message)
            return {'success': False, 'msg': msg}
        else:
            return {'success': True, 'msg': u""}
