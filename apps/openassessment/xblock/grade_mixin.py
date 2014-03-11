from xblock.core import XBlock
from openassessment.assessment import peer_api

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
            assessment_ui_model = self.get_assessment_module('peer-assessment')
            student_submission = self.get_user_submission(
                workflow["submission_uuid"]
            )
            student_score = workflow["score"]
            assessments = peer_api.get_assessments(student_submission["uuid"])
            median_scores = peer_api.get_assessment_median_scores(
                student_submission["uuid"],
                assessment_ui_model["must_be_graded_by"]
            )
            context["student_submission"] = student_submission
            context["peer_assessments"] = assessments
            context["rubric_criteria"] = self.rubric_criteria
            context["score"] = student_score
            for criterion in context["rubric_criteria"]:
                criterion["median_score"] = median_scores[criterion["name"]]
        elif workflow.get('status') == "waiting":
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
