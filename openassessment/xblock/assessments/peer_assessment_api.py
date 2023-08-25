import logging

from openassessment.assessment.errors import PeerAssessmentWorkflowError
from openassessment.assessment.api import peer as peer_api
from openassessment.xblock.data_conversion import (
    create_submission_dict
)
from openassessment.xblock.step_data_api import StepDataAPI

logger = logging.getLogger(__name__)


class PeerAssessmentAPI(StepDataAPI):
    def __init__(self, block, continue_grading = False):
        super().__init__(block, "peer-assessment")
        self._continue_grading = continue_grading
        self._submission_data = block.submission_data
        self._config_data = block.config_data

    def __repr__(self):
        return "{0}".format({
            "assessment": self.assessment,
            "continue_grading": self.continue_grading,
            "due_date": self.due_date,
            "file_upload_type": self.file_upload_type,
            "is_cancelled": self.is_cancelled,
            "is_complete": self.is_complete,
            "is_due": self.is_due,
            "is_not_available_yet": self.is_not_available_yet,
            "is_past_due": self.is_past_due,
            "is_peer": self.is_peer,
            "is_skipped": self.is_skipped,
            "start_date": self.start_date,
        })

    @property
    def assessment(self):
        return self.config_data.get_assessment_module("peer-assessment")

    @property
    def continue_grading(self):
        return self._continue_grading and self.workflow_data.is_peer_complete

    @property
    def file_upload_type(self):
        return self.config_data.file_upload_type

    @property
    def has_finished(self):
        finished, count = peer_api.has_finished_required_evaluating(
            self._block.submission_uuid,
            self.assessment["must_grade"]
        )
        return finished, count

    @property
    def is_cancelled(self):
        return self.workflow_data.is_cancelled

    @property
    def is_complete(self):
        finished = False
        if self.assessment:
            finished = self.has_finished[0]
        return self.workflow_data.is_done or finished

    @property
    def is_peer(self):
        return self.workflow_data.is_peer

    @property
    def is_skipped(self):
        return self.workflow_data.is_peer_skipped

    @property
    def student_item(self):
        return self.config_data.student_item_dict

    def format_submission_for_publish(self, peer_submission):
        student_item_dict = self.config_data.student_item_dict
        return {
            "requesting_student_id": student_item_dict["student_id"],
            "course_id": student_item_dict["course_id"],
            "item_id": student_item_dict["item_id"],
            "submission_returned_uuid": peer_submission["uuid"] if peer_submission else None,
        }

    def get_submission_dict(self, peer_sub):
        return create_submission_dict(peer_sub, self.config_data.prompts)

    def get_download_urls(self, peer_sub):
        return self._block.get_download_urls_from_submission(peer_sub)

    def get_peer_submission(self):
        peer_submission = False
        try:
            peer_submission = peer_api.get_submission_to_assess(
                self._submission_data.submission_uuid,
                self.assessment["must_be_graded_by"]
            )
            self._config_data.runtime.publish(
                self._block,
                "openassessmentblock.get_peer_submission",
                self.format_submission_for_publish(peer_submission)
            )
        except PeerAssessmentWorkflowError as err:
            logger.exception(err)
        return peer_submission
