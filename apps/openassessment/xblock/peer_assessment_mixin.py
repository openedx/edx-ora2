from xblock.core import XBlock
from openassessment.peer import api as peer_api
from openassessment.peer.api import PeerAssessmentWorkflowError


class PeerAssessmentMixin(object):

    @XBlock.json_handler
    def assess(self, data, suffix=''):
        """Place an assessment into OpenAssessment system
        """
        assessment_ui_model = self.get_assessment_module('peer-assessment')
        if assessment_ui_model:
            rubric_dict = {
                'criteria': self.rubric_criteria
            }
            assessment_dict = {
                "feedback": "Not yet implemented.",
                "options_selected": data["options_selected"],
            }
            assessment = peer_api.create_assessment(
                data["submission_uuid"],
                self.get_student_item_dict()["student_id"],
                int(assessment_ui_model.must_grade),
                int(assessment_ui_model.must_be_graded_by),
                assessment_dict,
                rubric_dict,
            )

            # Temp kludge until we fix JSON serialization for datetime
            assessment["scored_at"] = str(assessment["scored_at"])

        return {}


    @XBlock.handler
    def render_peer_assessment(self, data, suffix=''):
        assessment = self.get_assessment_module('peer-assessment')
        if assessment:
            peer_sub = self.get_peer_submission(self.get_student_item_dict(), assessment)
            context_dict = {"peer_submission": peer_sub}
        return self.render_assessment('static/html/oa_peer_assessment.html', context_dict)

    def get_peer_submission(self, student_item_dict, assessment):
        peer_submission = False
        try:
            peer_submission = peer_api.get_submission_to_assess(
                student_item_dict, assessment.must_be_graded_by
            )

            peer_submission = peer_api.get_submission_to_assess(
                student_item_dict,
                assessment.must_be_graded_by
            )

        except PeerAssessmentWorkflowError:
            # TODO: Log?
            pass
        return peer_submission

    def get_assessment_module(self, mixin_name):
        """Get a configured assessment module by name.
        """
        for assessment in self.rubric_assessments:
            if assessment.name == mixin_name:
                return assessment
