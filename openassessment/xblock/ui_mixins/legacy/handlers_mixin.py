"""JSON handlers for the old-style ORA UI"""

import logging

from xblock.core import XBlock

from openassessment.xblock.staff_area_mixin import require_course_staff
from openassessment.xblock.ui_mixins.legacy.peer_assessments.actions import peer_assess
from openassessment.xblock.ui_mixins.legacy.self_assessments.actions import self_assess
from openassessment.xblock.ui_mixins.legacy.staff_assessments.actions import (
    do_staff_assessment,
    staff_assess,
)
from openassessment.xblock.ui_mixins.legacy.student_training.actions import training_assess

from openassessment.xblock.ui_mixins.legacy.submissions.actions import (
    submit,
    save_submission,
)
from openassessment.xblock.utils.data_conversion import verify_assessment_parameters
from openassessment.xblock.ui_mixins.legacy.submissions.file_actions import (
    save_files_descriptions,
    upload_url,
    download_url,
    remove_uploaded_file,
)

logger = logging.getLogger(__name__)


class LegacyHandlersMixin:
    """
    Exposes actions (@XBlock.json_handlers) used in our legacy ORA UI
    """

    # Submissions

    @XBlock.json_handler
    def submit(self, data, suffix=""):  # pylint: disable=unused-argument
        """Submit a response for the student provided in data['submission']"""
        return submit(self.config_data, self.submission_data, data)

    @XBlock.json_handler
    def save_submission(self, data, suffix=""):  # pylint: disable=unused-argument
        """Save a draft response for the student under data['submission']"""
        return save_submission(self.config_data, self.submission_data, data)

    # File uploads

    @XBlock.json_handler
    def save_files_descriptions(self, data, suffix=""):  # pylint: disable=unused-argument
        return save_files_descriptions(self.config_data, self.submission_data, data)

    @XBlock.json_handler
    def upload_url(self, data, suffix=""):  # pylint: disable=unused-argument
        return upload_url(self.config_data, self.submission_data, data)

    @XBlock.json_handler
    def download_url(self, data, suffix=""):  # pylint: disable=unused-argument
        return download_url(self.submission_data, data)

    @XBlock.json_handler
    def remove_uploaded_file(self, data, suffix=""):  # pylint: disable=unused-argument
        return remove_uploaded_file(self.config_data, self.submission_data, data)

    # Assessments

    @XBlock.json_handler
    @verify_assessment_parameters
    def peer_assess(self, data, suffix=""):  # pylint: disable=unused-argument
        return peer_assess(self.api_data, data)

    @XBlock.json_handler
    @verify_assessment_parameters
    def self_assess(self, data, suffix=""):  # pylint: disable=unused-argument
        return self_assess(self.api_data, data)

    @XBlock.json_handler
    def training_assess(self, data, suffix=""):  # pylint: disable=unused-argument
        return training_assess(self.api_data, data)

    @XBlock.json_handler
    @require_course_staff("STUDENT_INFO")
    @verify_assessment_parameters
    def staff_assess(self, data, suffix=""):  # pylint: disable=unused-argument
        return staff_assess(self.api_data, data)

    # NOTE - Temporary surfacing
    def do_staff_assessment(self, data):
        return do_staff_assessment(self.api_data, data)

    # Utils

    @XBlock.json_handler
    def get_student_username(self, data, suffix=""):  # pylint: disable=unused-argument
        """
        Gets the username of the current student for use in team lookup.
        """
        anonymous_id = self.xmodule_runtime.anonymous_student_id
        return {"username": self.get_username(anonymous_id)}
