from openassessment.assessment.api import peer as peer_api
from submissions import api as submission_api
from openassessment.xblock.data_conversion import (
    clean_criterion_feedback,
    create_rubric_dict,
    create_submission_dict
)
from openassessment.xblock.resolve_dates import DISTANT_FUTURE
from openassessment.xblock.api.workflow import WorkflowAPI
from openassessment.xblock.api.block import BlockAPI
from .problem_closed import ProblemClosedAPI

class PeerAssessmentAPI:
    def __init__(self, block, continue_grading = False):
        self._block = block
        self._continue_grading = continue_grading
        self._block_api = BlockAPI(block)
        self._is_closed = ProblemClosedAPI(block, step="self-assessment")
        self._workflow = WorkflowAPI(block)

    @property
    def continue_grading(self):
        return self._continue_grading and self._workflow.is_peer_complete

    @property
    def is_due(self):
        return self._is_closed.is_due

    @property
    def due_date(self):
        return self._is_closed.due_date

    @property
    def assessment(self):
        return self._block_api.get_assessment_module("peer-assessment")

    @property
    def is_skipped(self):
        return self._workflow.is_peer_skipped

    @property
    def has_finished(self):
        finished, count = peer_api.has_finished_required_evaluating(
            self._block.submission_uuid,
            self.assessment["must_grade"]
        )
        return finished, count

    @property
    def is_cancelled(self):
        return self._workflow.is_cancelled

    @property
    def is_complete(self):
        finished = False
        if self.assessment:
            finished = self.has_finished[0]
        return self._workflow.is_done and finished

    @property
    def file_upload_type(self):
        return self._block_api.file_upload_type

    @property
    def is_past_due(self):
        return self._is_closed.is_past_due

    @property
    def is_not_available_yet(self):
        return self._is_closed.is_not_available_yet

    @property
    def is_peer(self):
        return self._workflow.is_peer

    @property
    def student_item(self):
        return self._block_api.student_item_dict

    def format_submission_for_publish(self):
        student_item_dict = self._block_api.student_item_dict
        peer_submission = peer_api.get_submission_to_assess(
            self._block.submission_uuid,
            self.assessment["must_be_graded_by"]
        )
        return {
            "requesting_student_id": student_item_dict["student_id"],
            "course_id": student_item_dict["course_id"],
            "item_id": student_item_dict["item_id"],
            "submission_returned_uuid": peer_submission["uuid"] if peer_submission else None,
        }

    def get_submission_dict(self, peer_sub):
        return create_submission_dict(peer_sub, self._block_api.prompts)

    def get_download_urls(self, peer_sub):
        return self._block.get_download_urls_from_submission(peer_sub)

    def get_peer_submission(self):
        return peer_api.get_submission_to_assess(
            self._block.submission_uuid,
            self.assessment["must_be_graded_by"]
        )

    @property
    def create_assessment(self, data):
        return peer_api.create_assessment(
            self._block.submission_uuid,
            self._block_api.student_item_dict["student_id"],
            data["options_selected"],
            clean_criterion_feedback(
                self._block_api.rubric_criteria_with_labels,
                data["criterion_feedback"]
            ),
            create_rubric_dict(self._block_api.prompts, self._block_api.rubric_criteria_with_labels),
            self.assessment["must_be_graded_by"]
        )
