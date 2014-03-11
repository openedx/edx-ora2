from xblock.core import XBlock
from openassessment.assessment.peer_api import get_assessments


class GradeMixin(object):
    """Grade Mixin introduces all handlers for displaying grades

    Abstracts all functionality and handlers associated with Grades.

    GradeMixin is a Mixin for the OpenAssessmentBlock. Functions in the
    GradeMixin call into the OpenAssessmentBlock functions and will not work
    outside of OpenAssessmentBlock.

    """

    @XBlock.handler
    def render_grade(self, data, suffix=''):
        workflow = self.get_workflow_info()

        status = workflow.get('status')
        context = {}
        if status == "done":
            path = 'openassessmentblock/grade/oa_grade_complete.html'
            context = {
                "score": workflow["score"],
                "assessments": [
                    assessment
                    for assessment in get_assessments(self.submission_uuid)
                ],
            }
        elif status == "waiting":
            path = 'openassessmentblock/grade/oa_grade_waiting.html'
        elif not status:
            path = 'openassessmentblock/grade/oa_grade_not_started.html'
        else:
            incomplete_steps = []
            if not workflow["status_details"]["peer"]["complete"]:
                incomplete_steps.append("Peer Assessment")
            if not workflow["status_details"]["self"]["complete"]:
                incomplete_steps.append("Self Assessment")
            context = {"incomplete_steps": incomplete_steps}
            path = 'openassessmentblock/grade/oa_grade_incomplete.html'

        return self.render_assessment(path, context)
