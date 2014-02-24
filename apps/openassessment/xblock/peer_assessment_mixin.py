from xblock.core import XBlock
from openassessment.peer import api as peer_api
from openassessment.peer.api import PeerAssessmentWorkflowError


class PeerAssessmentMixin(object):
    """The Peer Assessment Mixin for all Peer Functionality.

    Abstracts all functionality and handlers associated with Peer Assessment.
    All Peer Assessment API calls should be contained without this Mixin as
    well.

    PeerAssessmentMixin is a Mixin for the OpenAssessmentBlock. Functions in
    the PeerAssessmentMixin call into the OpenAssessmentBlock functions and
    will not work outside this scope.

    """

    @XBlock.json_handler
    def assess(self, data, suffix=''):
        """Place an assessment into OpenAssessment system

        Assess a Peer Submission.  Performs basic workflow validation to ensure
        that an assessment can be performed as this time.

        Args:
            data (dict): A dictionary containing information required to create
                a new peer assessment. Expecting attributes "points_earned",
                "total_value", and "submission_uuid". If these attributes are
                 not available, a new assessment cannot be stored.

        Returns:
            (tuple): A tuple containing the dictionary representation of the
            newly created assessment, and a "Success" string.

        """
        assessment = self.get_assessment_module('peer-assessment')
        if assessment:
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
        """Renders the Peer Assessment HTML section of the XBlock

        Generates the peer assessment HTML for the first section of an Open
        Assessment XBlock. See OpenAssessmentBlock.render_assessment() for
        more information on rendering XBlock sections.

        """
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
