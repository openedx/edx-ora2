from openassessment.peer import api as peer_api
from openassessment.peer.api import PeerAssessmentWorkflowError
from openassessment.xblock.assessment import Assessment


class PeerAssessment(Assessment):

    assessment_type = "peer-assessment"
    navigation_text = "Your assessment(s) of peer responses"
    path = "static/html/oa_peer_assessment.html"

    @classmethod
    def assess(cls, student_item_dict, rubric_criteria, data):
        """Place an assessment into Openassessment system
        """

        assessment_dict = {
            "points_earned": map(int, data["points_earned"]),
            "points_possible": sum(c['total_value'] for c in rubric_criteria),
            "feedback": "Not yet implemented.",
            }
        assessment = peer_api.create_assessment(
            data["submission_uuid"],
            student_item_dict["student_id"],
            int(cls.must_grade),
            int(cls.must_be_graded_by),
            assessment_dict
        )

        # Temp kludge until we fix JSON serialization for datetime
        assessment["scored_at"] = str(assessment["scored_at"])

        return assessment, "Success"

    def get_peer_submission(self, student_item_dict):
        peer_submission = False
        try:
            peer_submission = peer_api.get_submission_to_assess(
                student_item_dict, self.must_be_graded_by
            )
            # context_dict["peer_submission"] = peer_submission

            peer_submission = peer_api.get_submission_to_assess(
                student_item_dict,
                self.must_be_graded_by
            )

        except PeerAssessmentWorkflowError:
            # TODO: Log?
            pass
        return peer_submission