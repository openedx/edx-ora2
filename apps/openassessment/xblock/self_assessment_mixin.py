from xblock.core import XBlock
from openassessment.xblock.assessment_mixin import AssessmentMixin


class SelfAssessmentMixin(AssessmentMixin):

    @XBlock.handler
    def render_self_assessment(self, data, suffix=''):
        return self.render('static/html/oa_self_assessment.html')

