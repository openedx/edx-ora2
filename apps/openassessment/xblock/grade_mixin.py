from xblock.core import XBlock
from submissions.api import get_score


class GradeMixin(object):
    """Grade Mixin introduces all handlers for displaying grades

    Abstracts all functionality and handlers associated with Grades.

    GradeMixin is a Mixin for the OpenAssessmentBlock. Functions in the
    GradeMixin call into the OpenAssessmentBlock functions and will not work
    outside of OpenAssessmentBlock.

    """

    @XBlock.handler
    def render_grade(self, data, suffix=''):
        problem_open, date = self.is_open()
        workflowstate = "complete"  # TODO hook in workflow.
        context = {}
        if workflowstate == "complete":
            path = 'openassessmentblock/grade/oa_grade_complete.html'
            student_item = self.get_student_item_dict()
            scores = get_score(student_item)
            if scores:
                context = {"score": scores[0]}
            else:
                path = 'openassessmentblock/grade/oa_grade_waiting.html'
        elif not problem_open and date == "due":
            path = 'openassessmentblock/grade/oa_grade_closed.html'
        else:
            path = 'openassessmentblock/grade/oa_grade_incomplete.html'
            # TODO: How do we determine which modules are incomplete?

        return self.render_assessment(path, context)

