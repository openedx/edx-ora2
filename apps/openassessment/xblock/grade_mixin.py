"""
Grade step in the OpenAssessment XBlock.
"""
import copy

from django.utils.translation import ugettext as _
from xblock.core import XBlock

from openassessment.assessment import peer_api
from openassessment.assessment import self_api
from submissions import api as sub_api


class GradeMixin(object):
    """Grade Mixin introduces all handlers for displaying grades

    Abstracts all functionality and handlers associated with Grades.

    GradeMixin is a Mixin for the OpenAssessmentBlock. Functions in the
    GradeMixin call into the OpenAssessmentBlock functions and will not work
    outside of OpenAssessmentBlock.

    """

    @XBlock.handler
    def render_grade(self, data, suffix=''):
        """
        Render the grade step.

        Args:
            data: Not used.

        Kwargs:
            suffix: Not used.

        Returns:
            unicode: HTML content of the grade step.
        """
        # Retrieve the status of the workflow.  If no workflows have been
        # started this will be an empty dict, so status will be None.
        workflow = self.get_workflow_info()
        status = workflow.get('status')

        # Default context is empty
        context = {}

        # Render the grading section based on the status of the workflow
        try:
            if status == "done":
                path, context = self.render_grade_complete(workflow)
            elif status == "waiting":
                path = 'openassessmentblock/grade/oa_grade_waiting.html'
            elif status is None:
                path = 'openassessmentblock/grade/oa_grade_not_started.html'
            else:  # status is 'self' or 'peer', which implies that the workflow is incomplete
                path, context = self.render_grade_incomplete(workflow)
        except (sub_api.SubmissionError, peer_api.PeerAssessmentError, self_api.SelfAssessmentRequestError):
            return self.render_error(_(u"An unexpected error occurred."))
        else:
            return self.render_assessment(path, context)

    def render_grade_complete(self, workflow):
        """
        Render the grade complete state.

        Args:
            workflow (dict): The serialized Workflow model.

        Returns:
            tuple of context (dict), template_path (string)
        """
        feedback = peer_api.get_assessment_feedback(self.submission_uuid)
        feedback_text = feedback.get('feedback', '') if feedback else ''
        student_submission = sub_api.get_submission(workflow['submission_uuid'])
        peer_assessments = peer_api.get_assessments(student_submission['uuid'])
        self_assessment = self_api.get_assessment(student_submission['uuid'])
        has_submitted_feedback = peer_api.get_assessment_feedback(workflow['submission_uuid']) is not None

        # We retrieve the score from the workflow, which in turn retrieves
        # the score for our current submission UUID.
        # We look up the score by submission UUID instead of student item
        # to ensure that the score always matches the rubric.
        score = workflow['score']

        context = {
            'score': score,
            'feedback_text': feedback_text,
            'student_submission': student_submission,
            'peer_assessments': peer_assessments,
            'self_assessment': self_assessment,
            'rubric_criteria': copy.deepcopy(self.rubric_criteria),
            'has_submitted_feedback': has_submitted_feedback,
        }

        # Update the scores we will display to the user
        # Note that we are updating a *copy* of the rubric criteria stored in the XBlock field
        max_scores = peer_api.get_rubric_max_scores(self.submission_uuid)
        median_scores = peer_api.get_assessment_median_scores(student_submission["uuid"])
        if median_scores is not None and max_scores is not None:
            for criterion in context["rubric_criteria"]:
                criterion["median_score"] = median_scores[criterion["name"]]
                criterion["total_value"] = max_scores[criterion["name"]]

        return ('openassessmentblock/grade/oa_grade_complete.html', context)

    def render_grade_incomplete(self, workflow):
        """
        Render the grade incomplete state.

        Args:
            workflow (dict): The serialized Workflow model.

        Returns:
            tuple of context (dict), template_path (string)
        """
        incomplete_steps = []
        if not workflow["status_details"]["peer"]["complete"]:
            incomplete_steps.append("Peer Assessment")
        if not workflow["status_details"]["self"]["complete"]:
            incomplete_steps.append("Self Assessment")

        return (
            'openassessmentblock/grade/oa_grade_incomplete.html',
            {'incomplete_steps': incomplete_steps}
        )

    @XBlock.json_handler
    def submit_feedback(self, data, suffix=''):
        """
        Submit feedback on an assessment.

        Args:
            data (dict): Can provide keys 'feedback_text' (unicode) and 'feedback_options' (list of unicode).

        Kwargs:
            suffix (str): Unused

        Returns:
            Dict with keys 'success' (bool) and 'msg' (unicode)

        """
        feedback_text = data.get('feedback_text', u'')
        feedback_options = data.get('feedback_options', list())

        try:
            peer_api.set_assessment_feedback({
                'submission_uuid': self.submission_uuid,
                'feedback_text': feedback_text,
                'options': feedback_options,
            })
        except (peer_api.PeerAssessmentInternalError, peer_api.PeerAssessmentRequestError):
            return {'success': False, 'msg': _(u"Assessment feedback could not be saved.")}
        else:
            self.runtime.publish(
                self,
                "openassessmentblock.submit_feedback_on_assessments",
                {
                    'submission_uuid': self.submission_uuid,
                    'feedback_text': feedback_text,
                    'options': feedback_options,
                }
            )
            return {'success': True, 'msg': _(u"Feedback saved.")}
