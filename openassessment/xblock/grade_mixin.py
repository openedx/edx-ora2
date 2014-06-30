"""
Grade step in the OpenAssessment XBlock.
"""
import copy
from collections import defaultdict

from django.utils.translation import ugettext as _
from xblock.core import XBlock

from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import self as self_api
from openassessment.assessment.api import ai as ai_api
from openassessment.assessment.errors import SelfAssessmentError, PeerAssessmentError
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
                path, context = self.render_grade_waiting(workflow)
            elif status is None:
                path = 'openassessmentblock/grade/oa_grade_not_started.html'
            else:  # status is 'self' or 'peer', which implies that the workflow is incomplete
                path, context = self.render_grade_incomplete(workflow)
        except (sub_api.SubmissionError, PeerAssessmentError, SelfAssessmentError):
            return self.render_error(_(u"An unexpected error occurred."))
        else:
            return self.render_assessment(path, context)

    def render_grade_waiting(self, workflow):
        """
        Render the grade waiting state.

        Args:
            workflow (dict): The serialized Workflow model.

        Returns:
            tuple of context (dict) and template_path (string)

        """
        context = {
            "waiting": self.get_waiting_details(workflow["status_details"])
        }
        return 'openassessmentblock/grade/oa_grade_waiting.html', context

    def render_grade_complete(self, workflow):
        """
        Render the grade complete state.

        Args:
            workflow (dict): The serialized Workflow model.

        Returns:
            tuple of context (dict), template_path (string)
        """
        # Peer specific stuff...
        assessment_steps = self.assessment_steps
        submission_uuid = workflow['submission_uuid']

        example_based_assessment = None
        self_assessment = None
        feedback = None
        peer_assessments = []
        has_submitted_feedback = False

        if "peer-assessment" in assessment_steps:
            feedback = peer_api.get_assessment_feedback(submission_uuid)
            peer_assessments = peer_api.get_assessments(submission_uuid)
            has_submitted_feedback = feedback is not None

        if "self-assessment" in assessment_steps:
            self_assessment = self_api.get_assessment(submission_uuid)

        if "example-based-assessment" in assessment_steps:
            example_based_assessment = ai_api.get_latest_assessment(submission_uuid)

        feedback_text = feedback.get('feedback', '') if feedback else ''
        student_submission = sub_api.get_submission(submission_uuid)

        # We retrieve the score from the workflow, which in turn retrieves
        # the score for our current submission UUID.
        # We look up the score by submission UUID instead of student item
        # to ensure that the score always matches the rubric.
        # It's possible for the score to be `None` even if the workflow status is "done"
        # when all the criteria in the rubric are feedback-only (no options).
        score = workflow['score']

        context = {
            'score': score,
            'feedback_text': feedback_text,
            'student_submission': student_submission,
            'peer_assessments': peer_assessments,
            'self_assessment': self_assessment,
            'example_based_assessment': example_based_assessment,
            'rubric_criteria': self._rubric_criteria_with_feedback(peer_assessments),
            'has_submitted_feedback': has_submitted_feedback,
        }

        # Update the scores we will display to the user
        # Note that we are updating a *copy* of the rubric criteria stored in
        # the XBlock field
        max_scores = peer_api.get_rubric_max_scores(submission_uuid)
        median_scores = None
        if "peer-assessment" in assessment_steps:
            median_scores = peer_api.get_assessment_median_scores(submission_uuid)
        elif "self-assessment" in assessment_steps:
            median_scores = self_api.get_assessment_scores_by_criteria(submission_uuid)
        elif "example-based-assessment" in assessment_steps:
            median_scores = ai_api.get_assessment_scores_by_criteria(submission_uuid)

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
        def _is_incomplete(step):
            return (
                step in workflow["status_details"] and
                not workflow["status_details"][step]["complete"]
            )

        incomplete_steps = []
        if _is_incomplete("peer"):
            incomplete_steps.append(_("Peer Assessment"))
        if _is_incomplete("self"):
            incomplete_steps.append(_("Self Assessment"))

        return (
            'openassessmentblock/grade/oa_grade_incomplete.html',
            {'incomplete_steps': incomplete_steps}
        )

    @XBlock.json_handler
    def submit_feedback(self, data, suffix=''):
        """
        Submit feedback on an assessment.

        Args:
            data (dict): Can provide keys 'feedback_text' (unicode) and
                'feedback_options' (list of unicode).

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

    def _rubric_criteria_with_feedback(self, peer_assessments):
        """
        Add per-criterion feedback from peer assessments to the rubric criteria.
        Filters out empty feedback.

        Args:
            peer_assessments (list of dict): Serialized assessment models from the peer API.

        Returns:
            list of criterion dictionaries

        Example:
            [
                {
                    'name': 'Test name',
                    'prompt': 'Test prompt',
                    'order_num': 2,
                    'options': [...]
                    'feedback': [
                        'Good job!',
                        'Excellent work!',
                    ]
                },
                ...
            ]
        """
        criteria = copy.deepcopy(self.rubric_criteria)
        criteria_feedback = defaultdict(list)

        for assessment in peer_assessments:
            for part in assessment['parts']:
                if part['feedback']:
                    part_criterion_name = part['criterion']['name']
                    criteria_feedback[part_criterion_name].append(part['feedback'])

        for criterion in criteria:
            criterion_name = criterion['name']
            criterion['feedback'] = criteria_feedback[criterion_name]

        return criteria
