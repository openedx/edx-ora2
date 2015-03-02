"""
Leaderboard step in the OpenAssessment XBlock.
"""
from django.utils.translation import ugettext as _
from xblock.core import XBlock

from submissions import api as sub_api

from openassessment.assessment.errors import SelfAssessmentError, PeerAssessmentError
from openassessment.fileupload import api as file_upload_api
from openassessment.xblock.data_conversion import create_submission_dict


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
        Render the leaderboard.

        Args:
            data: Not used.

        Kwargs:
            suffix: Not used.

        Returns:
            unicode: HTML content of the leaderboard.
        """
        # Retrieve the status of the workflow.  If no workflows have been
        # started this will be an empty dict, so status will be None.
        workflow = self.get_workflow_info()
        status = workflow.get('status')

        # Render the grading section based on the status of the workflow
        try:
            if status == "done":
                path, context = self.render_leaderboard_complete(self.get_student_item_dict())
            else:  # status is 'self' or 'peer', which implies that the workflow is incomplete
                path, context = self.render_leaderboard_incomplete()
        except (sub_api.SubmissionError, PeerAssessmentError, SelfAssessmentError):
            return self.render_error(_(u"An unexpected error occurred."))
        else:
            return self.render_assessment(path, context)

    def render_leaderboard_complete(self, student_item_dict):
        """
        Render the leaderboard complete state.

        Args:
            student_item_dict (dict): The student item

        Returns:
            template_path (string), tuple of context (dict)
        """

        # Retrieve top scores from the submissions API
        # Since this uses the read-replica and caches the results,
        # there will be some delay in the request latency.
        scores = sub_api.get_top_submissions(
            student_item_dict['course_id'],
            student_item_dict['item_id'],
            student_item_dict['item_type'],
            self.leaderboard_show
        )
        for score in scores:
            if 'file_key' in score['content']:
                score['file'] = file_upload_api.get_download_url(score['content']['file_key'])
            if 'text' in score['content'] or 'parts' in score['content']:
                submission = {'answer': score.pop('content')}
                score['submission'] = create_submission_dict(submission, self.prompts)
            elif isinstance(score['content'], basestring):
                pass
            # Currently, we do not handle non-text submissions.
            else:
                score['submission'] = ""

            score.pop('content', None)

        context = { 'topscores': scores,
                    'allow_latex': self.allow_latex,
                  }
        return ('openassessmentblock/leaderboard/oa_leaderboard_show.html', context)

    def render_leaderboard_incomplete(self):
        """
        Render the grade incomplete state.

        Returns:
            template_path (string), tuple of context (dict)
        """
        return ('openassessmentblock/leaderboard/oa_leaderboard_waiting.html', {})
