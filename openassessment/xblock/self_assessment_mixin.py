""" A mixin for self Assessments. """


import logging

from webob import Response
from xblock.core import XBlock

from openassessment.assessment.api import self as self_api
from openassessment.workflow import api as workflow_api

from .data_conversion import (clean_criterion_feedback, create_rubric_dict, create_submission_dict,
                              verify_assessment_parameters)
from .resolve_dates import DISTANT_FUTURE
from .user_data import get_user_preferences
from .api.assessments.self_assessment import SelfAssessmentAPI

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class SelfAssessmentMixin:
    """The Self Assessment Mixin for all Self Assessment Functionality.

    Abstracts all functionality and handlers associated with Self Assessment.
    All Self Assessment API calls should be contained within this Mixin as
    well.

    SelfAssessmentMixin is a Mixin for the OpenAssessmentBlock. Functions in
    the SelfAssessmentMixin call into the OpenAssessmentBlock functions and
    will not work outside of OpenAssessmentBlock.
    """

    @XBlock.handler
    def render_self_assessment(self, data, suffix=''):  # pylint: disable=unused-argument
        if "self-assessment" not in self.assessment_steps:
            return Response("")

        try:
            path, context = self.self_path_and_context()
        except Exception:  # pylint: disable=broad-except
            msg = f"Could not retrieve self assessment for submission {self.submission_uuid}"
            logger.exception(msg)
            return self.render_error(self._("An unexpected error occurred."))
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
        # Import is placed here to avoid model import at project startup.
        from .api.assessments.self_assessment import SelfAssessmentAPI
        step_data = SelfAssessmentAPI(self)

        path = 'openassessmentblock/self/oa_self_unavailable.html'
        user_preferences = get_user_preferences(self.runtime.service(self, 'user'))

        context = {
            'allow_multiple_files': self.allow_multiple_files,
            'allow_latex': self.allow_latex,
            'prompts_type': self.prompts_type,
            "xblock_id": self.get_xblock_id(),
            'user_timezone': user_preferences['user_timezone'],
            'user_language': user_preferences['user_language']
        }

        # We display the due date whether the problem is open or closed.
        # If no date is set, it defaults to the distant future, in which
        # case we don't display the date.
        if step_data.is_due:
            context['self_due'] = step_data.due_date

        # If we haven't submitted yet, `workflow` will be an empty dict,
        # and `workflow_status` will be None.
        if step_data.is_cancelled:
            path = 'openassessmentblock/self/oa_self_cancelled.html'
            # Sets the XBlock boolean to signal to Message that it WAS able to grab a submission
            self.no_peers = True
        elif step_data.is_self_complete:
            path = 'openassessmentblock/self/oa_self_complete.html'
        elif step_data.is_complete
            if step_data.assessment is not None:
                path = 'openassessmentblock/self/oa_self_complete.html'
            elif step_data.problem_closed:
                if step_data.is_not_available_yet:
                    context["self_start"] = start_date
                    path = 'openassessmentblock/self/oa_self_unavailable.html'
                elif step_data.is_past_due:
                    path = 'openassessmentblock/self/oa_self_closed.html'
            else:
                context["rubric_criteria"] = self.rubric_criteria_with_labels
                context["self_submission"] = step_data.submission_dict
                if self.rubric_feedback_prompt is not None:
                    context["rubric_feedback_prompt"] = self.rubric_feedback_prompt

                if self.rubric_feedback_default_text is not None:
                    context['rubric_feedback_default_text'] = self.rubric_feedback_default_text

                # Determine if file upload is supported for this XBlock and what kind of files can be uploaded.
                context["file_upload_type"] = self.file_upload_type
                context['self_file_urls'] = step_data.file_urls

                path = 'openassessmentblock/self/oa_self_assessment.html'
        else:
            # No submission yet or in peer assessment
            path = 'openassessmentblock/self/oa_self_unavailable.html'

        return path, context

    @XBlock.json_handler
    @verify_assessment_parameters
    def self_assess(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Create a self-assessment for a submission.

        Args:
            data (dict): Must have the following keys:
                options_selected (dict): Dictionary mapping criterion names to option values.

        Returns:
            Dict with keys "success" (bool) indicating success/failure
            and "msg" (unicode) containing additional information if an error occurs.
        """

        if self.submission_uuid is None:
            return {
                'success': False,
                'msg': self._("You must submit a response before you can perform a self-assessment.")
            }

        try:
            assessment = SelfAssessmentApi(self).create_assessment(data)
            self.publish_assessment_event("openassessmentblock.self_assess", assessment)

            # After we've created the self-assessment, we need to update the workflow.
            self.update_workflow_status()
        except (self_api.SelfAssessmentRequestError, workflow_api.AssessmentWorkflowRequestError):
            logger.warning(
                "An error occurred while submitting a self assessment "
                "for the submission %s",
                self.submission_uuid,
                exc_info=True
            )
            msg = self._("Your self assessment could not be submitted.")
            return {'success': False, 'msg': msg}
        except (self_api.SelfAssessmentInternalError, workflow_api.AssessmentWorkflowInternalError):
            logger.exception(
                "An error occurred while submitting a self assessment "
                "for the submission %s",
                self.submission_uuid,
            )
            msg = self._("Your self assessment could not be submitted.")
            return {'success': False, 'msg': msg}
        else:
            return {'success': True, 'msg': ""}
