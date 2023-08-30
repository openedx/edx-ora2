from openassessment.xblock.ora_config_api import ORAConfigAPI
from openassessment.xblock.submissions.submissions_api import SubmissionAPI
from openassessment.xblock.workflow_api import WorkflowAPI
from openassessment.xblock.assessments.peer_assessment_api import PeerAssessmentAPI
from openassessment.xblock.assessments.self_assessment_api import SelfAssessmentAPI
from openassessment.xblock.assessments.staff_assessment_api import StaffAssessmentAPI
from openassessment.xblock.assessments.student_training_api import StudentTrainingAPI

class ORADataAccessor:
    def __init__(self, block):
        self._block = block

    @property
    def config_data(self):
        return ORAConfigAPI(self._block)

    @property
    def submission_data(self):
        return SubmissionAPI(self._block)

    @property
    def workflow_data(self):
        return WorkflowAPI(self._block)

    @property
    def self_assessment_data(self):
        return SelfAssessmentAPI(self._block)

    @property
    def staff_assessment_data(self):
        return StaffAssessmentAPI(self._block)

    @property
    def student_training_data(self):
        return StudentTrainingAPI(self._block)

    def peer_assessment_data(self, continue_grading=False):
        return PeerAssessmentAPI(self._block, continue_grading)
