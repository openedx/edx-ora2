"""
External API for ORA Self Assessment data
"""
from submissions import api as submission_api

from openassessment.assessment.api import self as self_api
from openassessment.xblock.apis.step_data_api import StepDataAPI
from openassessment.xblock.utils.data_conversion import create_submission_dict


class SelfAssessmentAPI(StepDataAPI):
    def __init__(self, block):
        super().__init__(block, "self-assessment")

    @property
    def is_self_complete(self):
        return self.workflow_data.is_self_complete

    @property
    def is_cancelled(self):
        return self.workflow_data.is_cancelled

    @property
    def is_self_active(self):
        return self.workflow_data.is_self

    @property
    def assessment(self):
        return self_api.get_assessment(self.workflow_data.workflow.get("submission_uuid"))

    @property
    def submission_uuid(self):
        return self._block.submission_uuid

    @property
    def submission(self):
        if self.submission_uuid:
            return submission_api.get_submission(self.submission_uuid)
        return None

    @property
    def submission_dict(self):
        if self.submission:
            return create_submission_dict(self.submission, self.config_data.prompts)
        return None

    @property
    def file_urls(self):
        if self.submission:
            return self._block.get_download_urls_from_submission(self.submission)
        return None

    @property
    def student_item_dict(self):
        return self.config_data.student_item_dict

    @property
    def rubric_criteria(self):
        return self.config_data.rubric_criteria

    @property
    def rubric_criteria_with_labels(self):
        return self.config_data.rubric_criteria

    @property
    def prompts(self):
        return self.config_data.rubric_criteria
