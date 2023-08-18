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
        self.block = BlockAPI(block)
        self._is_closed = ProblemClosedAPI(block, step="peer-assessment")
        self.workflow = WorkflowAPI(block)

    def __repr__(self):
        return "{0}".format({
            "is_closed": self._is_closed,
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
        return self.block.get_assessment_module("peer-assessment")

    @property
    def continue_grading(self):
        return self._continue_grading and self.workflow.is_peer_complete

    @property
    def due_date(self):
        return self._is_closed.due_date

    @property
    def file_upload_type(self):
        return self.block.file_upload_type

    @property
    def has_finished(self):
        finished, count = peer_api.has_finished_required_evaluating(
            self._block.submission_uuid,
            self.assessment["must_grade"]
        )
        return finished, count

    @property
    def is_cancelled(self):
        return self.workflow.is_cancelled

    @property
    def is_complete(self):
        finished = False
        if self.assessment:
            finished = self.has_finished[0]
        return self.workflow.is_done or finished

    @property
    def is_due(self):
        return self._is_closed.is_due

    @property
    def is_not_available_yet(self):
        return self._is_closed.is_not_available_yet

    @property
    def is_past_due(self):
        return self._is_closed.is_past_due

    @property
    def is_peer(self):
        return self.workflow.is_peer

    @property
    def is_skipped(self):
        return self.workflow.is_peer_skipped

    @property
    def start_date(self):
        return self._is_closed.start_date

    @property
    def student_item(self):
        return self.block.student_item_dict

    def format_submission_for_publish(self, peer_submission):
        student_item_dict = self.block.student_item_dict
        return {
            "requesting_student_id": student_item_dict["student_id"],
            "course_id": student_item_dict["course_id"],
            "item_id": student_item_dict["item_id"],
            "submission_returned_uuid": peer_submission["uuid"] if peer_submission else None,
        }

    def get_submission_dict(self, peer_sub):
        return create_submission_dict(peer_sub, self.block.prompts)

    def get_download_urls(self, peer_sub):
        return self._block.get_download_urls_from_submission(peer_sub)

    def get_peer_submission(self):
        return peer_api.get_submission_to_assess(
            self._block.submission_uuid,
            self.assessment["must_be_graded_by"]
        )
