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
    will not work outside of OpenAssessmentBlock

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
                int(assessment_ui_model["must_grade"]),
                int(assessment_ui_model["must_be_graded_by"]),
                assessment_dict,
                rubric_dict,
            )

            # Temp kludge until we fix JSON serialization for datetime
            assessment["scored_at"] = str(assessment["scored_at"])

        return {}


    @XBlock.handler
    def render_peer_assessment(self, data, suffix=''):
        """Renders the Peer Assessment HTML section of the XBlock

        Generates the peer assessment HTML for the first section of an Open
        Assessment XBlock. See OpenAssessmentBlock.render_assessment() for
        more information on rendering XBlock sections.

        """
        context_dict = {
            "rubric_criteria": self.rubric_criteria,
            "estimated_time": "20 minutes"  # TODO: Need to configure this.
        }
        path = 'openassessmentblock/peer/oa_peer_waiting.html'
        assessment = self.get_assessment_module('peer-assessment')
        if assessment:

            context_dict["must_grade"] = assessment["must_grade"]

            student_item = self.get_student_item_dict()


            finished, count = peer_api.has_finished_required_evaluating(
                student_item,
                assessment["must_grade"]
            )
            context_dict["graded"] = count
            if finished:
                path = "openassessmentblock/peer/oa_peer_complete.html"
            else:
                peer_sub = self.get_peer_submission(student_item, assessment)
                if peer_sub:
                    path = 'openassessmentblock/peer/oa_peer_assessment.html'
                    context_dict["peer_submission"] = peer_sub

            if assessment["must_grade"] - count == 1:
                context_dict["submit_button_text"] = "Submit your assessment & move onto next step."
            else:
                context_dict["submit_button_text"] = "Submit your assessment & move to response #{}".format(count + 1)


            problem_open, date = self.is_open()
            if not problem_open and date == "due" and not finished:
                path = 'openassessmentblock/peer/oa_peer_closed.html'


        return self.render_assessment(path, context_dict)

    def get_peer_submission(self, student_item_dict, assessment):
        peer_submission = False
        try:
            peer_submission = peer_api.get_submission_to_assess(
                student_item_dict, assessment["must_be_graded_by"]
            )

            peer_submission = peer_api.get_submission_to_assess(
                student_item_dict,
                assessment["must_be_graded_by"]
            )

        except PeerAssessmentWorkflowError:
            # TODO: Log?
            pass
        return peer_submission

    def get_assessment_module(self, mixin_name):
        """Get a configured assessment module by name.
        """
        for assessment in self.rubric_assessments:
            if assessment["name"] == mixin_name:
                return assessment
