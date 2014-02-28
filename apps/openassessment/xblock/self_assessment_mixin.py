from xblock.core import XBlock


class SelfAssessmentMixin(object):
    """The Self Assessment Mixin for all Self Assessment Functionality.

    Abstracts all functionality and handlers associated with Self Assessment.
    All Self Assessment API calls should be contained without this Mixin as
    well.

    SelfAssessmentMixin is a Mixin for the OpenAssessmentBlock. Functions in
    the SelfAssessmentMixin call into the OpenAssessmentBlock functions and
    will not work outside of OpenAssessmentBlock.

    """

    @XBlock.handler
    def render_self_assessment(self, data, suffix=''):
        path = 'openassessmentblock/self/oa_self_closed.html'
        context_dict = {}
        student_item = self.get_student_item_dict()
        student_submission = self.get_user_submission(student_item)
        if student_submission:
            path = 'openassessmentblock/self/oa_self_assessment.html'
            context_dict = {
                "rubric_criteria": self.rubric_criteria,
                "estimated_time": "20 minutes",  # TODO: Need to configure this.
                "self_submission": student_submission,
                "step_status": "Grading"
            }
        return self.render_assessment(path, context_dict)
