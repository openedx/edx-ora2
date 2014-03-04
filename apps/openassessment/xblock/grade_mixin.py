from xblock.core import XBlock
from openassessment.assessment.peer_api import get_assessments
from openassessment.workflow import api as workflow_api


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
        workflow = self.get_workflow_info()
        context = {}
        if workflow.get('status') == "done":
            path = 'openassessmentblock/grade/oa_grade_complete.html'
            context = {
                "score": workflow["score"],
                "assessments": [
                    assessment
                    for assessment in get_assessments(self.submission_uuid)
                ],
            }
        elif workflow.get('status') == "waiting":
            path = 'openassessmentblock/grade/oa_grade_waiting.html'
        elif not problem_open and date == "due":
            path = 'openassessmentblock/grade/oa_grade_closed.html'
        else:
            path = 'openassessmentblock/grade/oa_grade_incomplete.html'
            # TODO: How do we determine which modules are incomplete?

        return self.render_assessment(path, context)
