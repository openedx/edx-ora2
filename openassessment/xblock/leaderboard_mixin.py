"""
Leaderboard step in the OpenAssessment XBlock.
"""
import copy
from collections import defaultdict

from django.utils.translation import ugettext as _
from xblock.core import XBlock

from openassessment.assessment.api import peer as peer_api
from openassessment.assessment.api import leaderboard as leaderboard_api
from openassessment.assessment.errors import SelfAssessmentError, PeerAssessmentError
from submissions import api as sub_api


class LeaderboardMixin(object):
    """Leaderboard Mixin introduces all handlers for displaying the leaderboard

    Abstracts all functionality and handlers associated with the Leaderboard.

    Leaderboard is a Mixin for the OpenAssessmentBlock. Functions in the
    Leaderboard call into the OpenAssessmentBlock functions and will not work
    outside of OpenAssessmentBlock.

    """

    @XBlock.handler
    def render_leaderboard(self, data, suffix=''):
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

        print "RENDERING LEADERBOARD"
        print status

        # Default context is empty
        context = {}

        # Render the grading section based on the status of the workflow
        try:
            if status == "done":
                path, context = self.render_leaderboard_complete(workflow)
                print path
            elif status == "waiting":
                path = 'openassessmentblock/leaderboard/oa_leaderboard_waiting.html'
            elif status is None:
                path = 'openassessmentblock/leaderboard/oa_leaderboard_waiting.html'
            else:  # status is 'self' or 'peer', which implies that the workflow is incomplete
                path, context = self.render_leaderboard_incomplete(workflow)
        except (sub_api.SubmissionError, PeerAssessmentError, SelfAssessmentError):
            return self.render_error(_(u"An unexpected error occurred."))
        else:
            return self.render_assessment(path, context)

    def render_leaderboard_complete(self, workflow):
        print "LEADERBOARD COMPLETE"
        """
        Render the grade complete state.

        Args:
            workflow (dict): The serialized Workflow model.

        Returns:
            tuple of context (dict), template_path (string)
        """

        context = {
            'topscores': leaderboard_api.get_leaderboard()
        }
        #
        # # Update the scores we will display to the user
        # # Note that we are updating a *copy* of the rubric criteria stored in
        # # the XBlock field
        # max_scores = peer_api.get_rubric_max_scores(submission_uuid)
        # if "peer-assessment" in assessment_steps:
        #     median_scores = peer_api.get_assessment_median_scores(submission_uuid)
        # elif "self-assessment" in assessment_steps:
        #     median_scores = self_api.get_assessment_scores_by_criteria(submission_uuid)

        # if median_scores is not None and max_scores is not None:
        #     for criterion in context["rubric_criteria"]:
        #         criterion["median_score"] = median_scores[criterion["name"]]
        #         criterion["total_value"] = max_scores[criterion["name"]]

        return ('openassessmentblock/leaderboard/oa_leaderboard_show.html', context)

    def render_leaderboard_incomplete(self, workflow):
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
            'openassessmentblock/leaderboard/oa_leaderboard_waiting.html',
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
                    part_criterion_name = part['option']['criterion']['name']
                    criteria_feedback[part_criterion_name].append(part['feedback'])

        for criterion in criteria:
            criterion_name = criterion['name']
            criterion['feedback'] = criteria_feedback[criterion_name]

        return criteria
