from openassessment.assessment.api import peer as peer_api
from submissions import api as submission_api

from ..data_conversion import (
    create_submission_dict
)
from ..resolve_dates import DISTANT_FUTURE
from .problem_closed import ProblemClosedAPI
from ..workflow import WorkflowAPI
from ..block import BlockAPI

class PeerAssessmentAPI:
    def __init__(self, block):
        self._raw_block
        self._block = BlockAPI(block)
        self._is_closed = ProblemClosedAPI(block.is_closed(step="self-assessment"))
        self._workflow = WorkflowAPI(block):

    @property
    def is_due(self):
        return self._is_closed.is_due

    @property
    def due_date(self):
        return self._is_closed.due_date

    @property
    def assessment(self):
        return peer_api.get_assessment(workflow.get('submission_uuid'))

    @property
    def is_skipped(self):
        return self._workflow.is_peer_skipped

    @propety
    def is_complete(self):
        return self._workflow.is_peer_complete

    @property
    def has_finished(self):
        finished, count = peer_api.has_finished_required_evaluating(
            self.block.submission_uuid,
            self.assessment["must_grade"]
        )
        return finished, count

    @property
    def is_cancelled(self):
        return self._workflow.is_cancelled

    @property
    def is_complete(self):
        return self._workflow.is_done

    @property
    def file_upload_type(self):
        return self._block.file_upload_type

    @property
    def is_past_due(self):
        return self._is_closed.is_past_due

    @property
    def is_not_available_yet(self):
        return self._is_closed.is_not_available_yet

    @property
    def is_peer
        return self._workflow.is_peer

    def format_submission_for_publish(self, submission):
        student_item_dict = self._block.student_item_dict
        peer_submission = peer_api.get_submission_to_assess(
            self._block.submission_uuid,
            self.assessment["must_be_graded_by"]
        )
        return {
            "requesting_student_id": student_item_dict["student_id"],
            "course_id": student_item_dict["course_id"],
            "item_id": student_item_dict["item_id"],
            "submission_returned_uuid": submission["uuid"] if submission else None,
        }

    def get_submission_dict(self, peer_sub):
        return create_submission_dict(peer_sub, self._block.prompts)

    def get_download_urls(self, peer_sub):
        return self._raw_block.get_download_urls_from_submission(peer_sub)

    def get_peer_submission(self):
        return peer_api.get_submission_to_assess(
            self._block.submission_uuid,
            self.assessment["must_be_graded_by"]
        )

    @property
    def assessment_ui_model(self):
        return self.block.get_assessment_module("peer-assessment")

    def create_assessment(self, data):
        return peer_api.create_assessment(
            self._block.submission_uuid,
            self._block.student_item_dict["student_id"],
            data["options_selected"],
            clean_criterion_feedback(
                self._block.rubric_criteria_with_labels,
                data["criterion_feedback"]
            ),
            create_rubric_dict(self._block.prompts, self._block.rubric_criteria_with_labels),
            self.assessment_ui_model["must_be_graded_by"]
        )
