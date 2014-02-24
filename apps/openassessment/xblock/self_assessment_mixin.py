from xblock.core import XBlock


class SelfAssessmentMixin(object):

    @XBlock.handler
    def render_self_assessment(self, data, suffix=''):
        return self.render_assessment('static/html/oa_self_assessment.html')

