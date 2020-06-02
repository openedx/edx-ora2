"""
Leaderboard step in the OpenAssessment XBlock.
"""
from __future__ import absolute_import

import logging
import six

from django.utils.translation import ugettext as _

from xblock.core import XBlock
from openassessment.assessment.errors import PeerAssessmentError, SelfAssessmentError
from openassessment.fileupload import api as file_upload_api
from openassessment.fileupload.exceptions import FileUploadError
from openassessment.xblock.data_conversion import create_submission_dict

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class LeaderboardMixin:
    """Leaderboard Mixin introduces all handlers for displaying the leaderboard

    Abstracts all functionality and handlers associated with the Leaderboard.

    Leaderboard is a Mixin for the OpenAssessmentBlock. Functions in the
    Leaderboard call into the OpenAssessmentBlock functions and will not work
    outside of OpenAssessmentBlock.

    """

    @XBlock.handler
    def render_leaderboard(self, data, suffix=''):  # pylint: disable=unused-argument
        """
        Render the leaderboard.

        Args:
            data: Not used.

        Kwargs:
            suffix: Not used.

        Returns:
            unicode: HTML content of the leaderboard.
        """
        # Import is placed here to avoid model import at project startup.
        from submissions import api as sub_api
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
        # Import is placed here to avoid model import at project startup.
        from submissions import api as sub_api

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
            score['files'] = []
            if 'file_keys' in score['content']:
                file_keys = score['content'].get('file_keys', [])
                descriptions = score['content'].get('files_descriptions', [])
                file_names = score['content'].get('files_name', [])
                for idx, key in enumerate(file_keys):
                    file_download_url = self._get_file_download_url(key)
                    if file_download_url:
                        file_description = descriptions[idx] if idx < len(descriptions) else ''
                        file_name = file_names[idx] if idx < len(file_names) else ''
                        score['files'].append((file_download_url, file_description, file_name, False))

            elif 'file_key' in score['content']:
                file_download_url = self._get_file_download_url(score['content']['file_key'])
                if file_download_url:
                    score['files'].append((file_download_url, '', '', False))
            if 'text' in score['content'] or 'parts' in score['content']:
                submission = {'answer': score.pop('content')}
                score['submission'] = create_submission_dict(submission, self.prompts)
            elif isinstance(score['content'], six.string_types):
                pass
            # Currently, we do not handle non-text submissions.
            else:
                score['submission'] = ""

            score.pop('content', None)

        context = {'topscores': scores,
                   'allow_latex': self.allow_latex,
                   'prompts_type': self.prompts_type,
                   'file_upload_type': self.file_upload_type,
                   'xblock_id': self.get_xblock_id()}

        return 'openassessmentblock/leaderboard/oa_leaderboard_show.html', context

    def render_leaderboard_incomplete(self):
        """
        Render the grade incomplete state.

        Returns:
            template_path (string), tuple of context (dict)
        """
        return 'openassessmentblock/leaderboard/oa_leaderboard_waiting.html', {'xblock_id': self.get_xblock_id()}

    def _get_file_download_url(self, file_key):
        """
        Internal function for retrieving the download url at which the file that corresponds
        to the file_key can be downloaded.

        Arguments:
            file_key (string): Corresponding file key.
        Returns:
            file_download_url (string) or empty string in case of error.
        """
        try:
            file_download_url = file_upload_api.get_download_url(file_key)
        except FileUploadError as exc:
            logger.exception(u'FileUploadError: URL retrieval failed for key {file_key} with error {error}'.format(
                file_key=file_key,
                error=exc
            ))
            file_download_url = ''
        return file_download_url
