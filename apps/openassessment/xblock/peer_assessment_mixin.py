from xblock.core import XBlock
from openassessment.peer import api as peer_api
from openassessment.peer.api import PeerAssessmentWorkflowError


class PeerAssessmentMixin(object):

    @XBlock.json_handler
    def assess(self, data, suffix=''):
        """Place an assessment into OpenAssessment system
        """
        with self.get_assessment_module('peer-assessment') as assessment:

            assessment_dict = {
                "points_earned": map(int, data["points_earned"]),
                "points_possible": sum(c['total_value'] for c in self.rubric_criteria),
                "feedback": "Not yet implemented.",
            }
            assessment = peer_api.create_assessment(
                data["submission_uuid"],
                self.get_student_item_dict()["student_id"],
                int(assessment.must_grade),
                int(assessment.must_be_graded_by),
                assessment_dict
            )


            # Temp kludge until we fix JSON serialization for datetime
            assessment["scored_at"] = str(assessment["scored_at"])

            return assessment, "Success"

    @XBlock.handler
    def render_peer_assessment(self, data, suffix=''):
        with self.get_assessment_module('peer-assessment') as assessment:
            context_dict = {"peer_submission": self.get_peer_submission(
                self.get_student_item_dict(),
                assessment
            )}
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
