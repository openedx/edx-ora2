import copy

from django.utils.translation import ugettext as _
from xblock.core import XBlock

from openassessment.assessment import peer_api
from submissions import api as submissions_api



class GradeMixin(object):
    """Grade Mixin introduces all handlers for displaying grades

    Abstracts all functionality and handlers associated with Grades.

    GradeMixin is a Mixin for the OpenAssessmentBlock. Functions in the
    GradeMixin call into the OpenAssessmentBlock functions and will not work
    outside of OpenAssessmentBlock.

    """

    def __stackinfo(self):
        import inspect
        stack = inspect.stack()
        return str(stack[0][1]) +':L'+str(stack[0][2])+':'+ str(stack[0][3]) +'()'

    @XBlock.handler
    def render_grade(self, data, suffix=''):
        workflow = self.get_workflow_info()
        status = workflow.get('status')
        context = {}
        if status == "done":
            max_scores = peer_api.get_rubric_max_scores(self.submission_uuid)
            path = 'openassessmentblock/grade/oa_grade_complete.html'
            assessment_ui_model = self.get_assessment_module('peer-assessment')
            student_submission = self.get_user_submission(
                workflow["submission_uuid"]
            )
            student_score = workflow["score"]
            assessments = peer_api.get_assessments(student_submission["uuid"])
            peer_assessments = []
            self_assessment = None
            for assessment in assessments:
                if assessment["score_type"] == "PE":
                    peer_assessments.append(assessment)
                else:
                    self_assessment = assessment
            peer_assessments = peer_assessments[:assessment_ui_model["must_grade"]]
            median_scores = peer_api.get_assessment_median_scores(
                student_submission["uuid"],
                assessment_ui_model["must_be_graded_by"]
            )
            context["student_submission"] = student_submission
            context["peer_assessments"] = peer_assessments
            context["self_assessment"] = self_assessment
            context["rubric_criteria"] = copy.deepcopy(self.rubric_criteria)
            context["score"] = student_score

            if median_scores is not None and max_scores is not None:
                for criterion in context["rubric_criteria"]:
                    criterion["median_score"] = median_scores[criterion["name"]]
                    criterion["total_value"] = max_scores[criterion["name"]]

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

    @XBlock.json_handler
    def feedback_submit(self, data, suffix=''):
        """Attach the Assessment Feedback text to some submission."""
        submission_uuid = self.submission_uuid
        assessment_feedback = data.get('feedback', '')
        raise Exception, "jrbl everything worked up to here" # DEBUG
        if not assessment_feedback:
            return {'success': False, 'msg': _(u"No feedback given, so none recorded")}
        feedback_dict = submissions_api.get_assessment_feedback(submission_uuid)
        feedback_dict['feedback'] = assessment_feedback
        __ = submissions_api.set_assessment_feedback(feedback_dict)
        return {'success': True, 'msg': _(u"Feedback saved!")}
