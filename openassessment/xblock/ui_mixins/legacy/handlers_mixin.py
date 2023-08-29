"""
JSON handlers for the old-style ORA UI
"""


from xblock.core import XBlock
from openassessment.xblock.ui_mixins.legacy.peer_assessments.actions import peer_assess
from openassessment.xblock.ui_mixins.legacy.self_assessments.actions import self_assess
from openassessment.xblock.ui_mixins.legacy.student_training.actions import training_assess
from openassessment.xblock.ui_mixins.legacy.submissions.actions import (
    LegacySubmissionActions,
)


class LegacyHandlersMixin(LegacySubmissionActions):
    """
    Exposes actions (@XBlock.json_handlers) used in our legacy ORA UI
    """

    # Submissions

    @XBlock.json_handler
    def submit(self, data, suffix=""):  # pylint: disable=unused-argument
        """ Submit a response for the student provided in data['submission'] """
        return LegacySubmissionActions.submit(
            self.config_data, self.submission_data, data
        )

    @XBlock.json_handler
    def save_submission(self, data, suffix=""):  # pylint: disable=unused-argument
        """ Save a draft response for the student under data['submission'] """
        return LegacySubmissionActions.save_submission(self.config_data, self.submission_data, data)

    # File uploads

    @XBlock.json_handler
    def save_files_descriptions(self, data, suffix=""):  # pylint: disable=unused-argument
        return LegacySubmissionActions.save_files_descriptions(self.config_data, self.submission_data, data)

    @XBlock.json_handler
    def upload_url(self, data, suffix=""):  # pylint: disable=unused-argument
        return LegacySubmissionActions.upload_url(self.config_data, self.submission_data, data)

    @XBlock.json_handler
    def download_url(self, data, suffix=""):  # pylint: disable=unused-argument
        return LegacySubmissionActions.download_url(self.submission_data, data)

    @XBlock.json_handler
    def remove_uploaded_file(self, data, suffix=""):  # pylint: disable=unused-argument
        return LegacySubmissionActions.remove_uploaded_file(self.config_data, self.submission_data, data)

    # Assessments

    @XBlock.json_handler
    def peer_assess(self, data, suffix=""):
        return peer_assess(self.api_data, data)

    @XBlock.json_handler
    def self_assess(self, data):
        return self_assess(self.api_data, data)

    @XBlock.json_handler
    def training_assess(self, data):
        return training_assess(self.api_data, data)

    # Utils
    @XBlock.json_handler
    def get_student_username(self, data, suffix):  # pylint: disable=unused-argument
        """
        Gets the username of the current student for use in team lookup.
        """
        anonymous_id = self.xmodule_runtime.anonymous_student_id
        return {"username": self.get_username(anonymous_id)}