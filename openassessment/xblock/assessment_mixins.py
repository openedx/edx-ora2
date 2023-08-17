from openassessment.xblock.peer_assessment_mixin import PeerAssessmentMixin
from openassessment.xblock.self_assessment_mixin import SelfAssessmentMixin
from openassessment.xblock.staff_assessment_mixin import StaffAssessmentMixin


class AssessmentMixins(PeerAssessmentMixin, SelfAssessmentMixin, StaffAssessmentMixin):
    pass
