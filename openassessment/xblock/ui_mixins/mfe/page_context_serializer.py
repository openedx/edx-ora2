"""
Serializers for ORA's BFF.

These are the response shapes that power the MFE implementation of the ORA UI.
"""
# pylint: disable=abstract-method

from rest_framework.fields import ValidationError, CharField
from rest_framework.serializers import (
    BooleanField,
    DateTimeField,
    IntegerField,
    Serializer,
    SerializerMethodField,
)
from openassessment.xblock.ui_mixins.mfe.assessment_serializers import (
    AssessmentGradeSerializer,
    AssessmentResponseSerializer,
)
from openassessment.xblock.ui_mixins.mfe.constants import handler_suffixes
from openassessment.xblock.ui_mixins.mfe.submission_serializers import DraftResponseSerializer, SubmissionSerializer
from openassessment.xblock.ui_mixins.mfe.serializer_utils import STEP_NAME_MAPPINGS, CharListField


class AssessmentScoreSerializer(Serializer):
    """
    Returns:
    {
        earned: (Int) How many points were you awarded by peers?
        possible: (Int) What was the max possible grade?
    }
    """

    earned = IntegerField(source="points_earned", required=False)
    possible = IntegerField(source="points_possible", required=False)


class ClosedInfoSerializer(Serializer):
    """Serialize closed info from a given assessment step API"""

    closed = BooleanField(source="problem_closed")
    closedReason = SerializerMethodField()

    def get_closedReason(self, instance):
        closed_reason = instance.closed_reason

        if closed_reason == "start":
            return "notAvailableYet"
        if closed_reason == "due":
            return "pastDue"
        return None


class StepInfoBaseSerializer(ClosedInfoSerializer):
    """Fields and logic shared for info of all assessment steps"""

    def to_representation(self, instance):
        # When we haven't reached this step, don't return any info
        if not instance.has_reached_step:
            return None
        return super().to_representation(instance)


class TeamInfoSerializer(Serializer):
    """
    Returns: Empty object for individual assignments, or the below for team assignments
    {
        teamName: (String)
        teamUsernames: (Array [String])

        // Learner submitted on a previous team
        previousTeamName: (String / Nullable)

        // Current team has submitted response (learner may not have)
        hasSubmitted: (Bool)
    }
    """
    teamName = CharField(source="team_name")
    teamUsernames = CharListField(source="team_usernames")
    previousTeamName = CharField(source="previous_team_name", allow_null=True)
    hasSubmitted = BooleanField(source="has_submitted")

    def to_representation(self, instance):
        # If there's no team name, there's no team info to show
        if 'team_name' not in instance:
            return {}
        return super().to_representation(instance)


class SubmissionStepInfoSerializer(ClosedInfoSerializer):
    """
    Returns:
        {
            closed: (Bool / Null for Assessment)
            closedReason: (Enum/ Null if open), one of "notAvailable", "pastDue"

            hasSubmitted: (Bool, Null for Assessment)
            hasCancelled: (Bool, Null for Assessment)

            // Team info needed for team responses - Empty object for individual submissions
            teamInfo: (Object, can be empty / Null for assessment)
            {
                See TeamInfoSerializer
            }
        }
    """

    hasSubmitted = BooleanField(source="has_submitted")
    hasCancelled = BooleanField(source="has_been_cancelled", default=False)
    cancelledBy = CharField(source="cancelled_by")
    cancelledAt = DateTimeField(source="cancelled_at")
    teamInfo = SerializerMethodField()

    def get_teamInfo(self, instance):
        if not instance.is_team_assignment:
            return {}
        team_info, _ = instance.get_submission_team_info(instance.workflow)

        return TeamInfoSerializer(team_info).data


class StudentTrainingStepInfoSerializer(StepInfoBaseSerializer):
    """
    Returns:
        {
            closed: (Bool)
            closedReason: (Enum/ Null if open), one of "notAvailable", "pastDue"
            numberOfAssessmentsCompleted: (Int), progress through required assessments
            expectedRubricSelections: (List of rubric names and selections)
        }
    """

    numberOfAssessmentsCompleted = IntegerField(source="num_completed")
    expectedRubricSelections = SerializerMethodField()

    def get_expectedRubricSelections(self, instance):
        """
        Get expected rubric selections for Student Training step

        WARN: It is critical we do not hit this if we are not on the student
              training step, as loading an example will create a workflow.

        Returns: {
            <Criterion Index>: (Number) Selected criterion option index
            <Criterion Index>: (Number) Selected criterion option index
            ... etc.
        }
        """
        criteria = instance.example["rubric"]['criteria']
        options_selected = instance.example["options_selected"]

        expected_rubric_selections = {}
        for criterion in criteria:
            for option in criterion['options']:
                if option['name'] == options_selected[criterion['name']]:
                    expected_rubric_selections[criterion['order_num']] = option['order_num']
                    break

        return expected_rubric_selections


class PeerStepInfoSerializer(StepInfoBaseSerializer):
    """
    Returns:
        {
            closed: (Bool)
            closedReason: (Enum/ Null if open), one of "notAvailable", "pastDue"
            numberOfAssessmentsCompleted: (Int) Progress through required assessments
            isWaitingForSubmissions: (Bool) We've run out of peers to grade, waiting for more submissions
            numberOfReceivedAssessments: (Int) How many assessments has this response received
        }
    """

    numberOfAssessmentsCompleted = IntegerField(source="num_completed")
    isWaitingForSubmissions = BooleanField(source="waiting_for_submissions_to_assess")
    numberOfReceivedAssessments = IntegerField(source="num_received")


class SelfStepInfoSerializer(StepInfoBaseSerializer):
    """
    Extra info required for the Self Step
    Returns {
        "closed"
        "closedReason"
    }
    """


class StepInfoSerializer(Serializer):
    """
    Required context:
    * step - The active workflow step

    Returns:
    * Peer or learner training-specific data if on those steps
    * Empty dict for remaining steps
    """

    requires_context = True

    submission = SubmissionStepInfoSerializer(source="submission_data")
    studentTraining = StudentTrainingStepInfoSerializer(source="student_training_data")
    peer = PeerStepInfoSerializer(source="peer_assessment_data")
    _self = SelfStepInfoSerializer(source="self_data")

    def get_fields(self):
        # Hack to name one of the output fields "self", a reserved word
        result = super().get_fields()
        _self = result.pop("_self", None)
        result["self"] = _self
        return result

    def to_representation(self, instance):
        """
        Hook output to remove fields that are not part of the active step.
        """

        if "student-training" not in instance.assessment_steps:
            self.fields.pop("studentTraining")
        if "peer-assessment" not in instance.assessment_steps:
            self.fields.pop("peer")
        if "self-assessment" not in instance.assessment_steps:
            self.fields.pop("self")

        return super().to_representation(instance)


class ProgressSerializer(Serializer):
    """
    Data about the progress of a user through their ORA workflow.

    Args: WorkflowAPI

    Returns:
    {
        // What step are we on? An index to the configuration from ORA config call.
        activeStepName: (String) one of ["submission", "studentTraining", "peer", "self", "staff", "done]
        activeStepInfo: (Object) Specific info for the active step
    }
    """

    activeStepName = SerializerMethodField()
    stepInfo = StepInfoSerializer(source="*")

    def get_activeStepName(self, instance):
        """Return the active step name"""
        if not instance.workflow_data.has_workflow or instance.workflow_data.is_cancelled:
            return "submission"
        else:
            return STEP_NAME_MAPPINGS[instance.workflow_data.status]


class PageDataSerializer(Serializer):
    """
    Data for rendering a page in the ORA MFE

    Requires context to differentiate between Assessment and Submission views

    Args:
    * ORA XBlock (self)

    Context:
    * current_workflow_step - The Workflow step
    * requested_step - The step a user is currently requesting data for

    NOTE: This serializer assumes you have *already* checked safety of a user visiting this step and
    blocked unintended access, as requesting data for some steps will start that workflow step.
    """

    requires_context = True

    progress = ProgressSerializer(source="*")
    response = SerializerMethodField()
    assessment = SerializerMethodField()

    def to_representation(self, instance):
        if "requested_step" not in self.context:
            raise ValidationError("Missing required context: requested_step")
        if "current_workflow_step" not in self.context:
            raise ValidationError("Missing required context: current_workflow_step")

        if self.context.get("requested_step", "submission") not in handler_suffixes.STEP_SUFFIXES:
            raise ValidationError(f"Bad step name: {self.context.get('requested_step')}")

        return super().to_representation(instance)

    def get_response(self, instance):
        """
        we get the user's draft / complete submission.
        """
        # pylint: disable=broad-exception-raised

        requested_step = self.context.get("requested_step")
        current_workflow_step = self.context.get("current_workflow_step")

        # When we are requesting page w/out active step, no response is needed
        if requested_step is None:
            return None

        # If a student's submission was cancelled, don't show any data, workflows are paused.
        elif current_workflow_step == "cancelled":
            return None

        # Submission (draft OR completed)
        elif requested_step == "submission":
            learner_submission_data = instance.get_learner_submission_data()

            # Draft response
            if not instance.submission_data.has_submitted:
                return DraftResponseSerializer(learner_submission_data).data

            # Submitted response
            return SubmissionSerializer(learner_submission_data).data

        # Student Training - return next example to practice
        elif requested_step == "studentTraining":
            response = instance.student_training_data.example

        # Peer
        elif requested_step == "peer":

            # If this is the step we're on (not continued grading), get a new submission to assess
            if current_workflow_step == "peer":
                response = instance.peer_assessment_data().get_peer_submission()

            # We're revisiting the peer step, get me my active assessment, if I have one in progress...
            # Otherwise, we're using a separate endpoint to request extra peer submissions to grade.
            else:
                response = instance.peer_assessment_data().get_active_assessment_submission()

        # Self / Done - Return your response to view / assess
        elif requested_step in ("self", "done"):
            learner_submission_data = instance.get_learner_submission_data()
            return SubmissionSerializer(learner_submission_data).data

        # Steps without a necessary response
        elif requested_step in ("staff"):
            response = None

        return AssessmentResponseSerializer(response).data

    def get_assessment(self, instance):
        """
         we get an assessment for the current assessment step.
        """
        # Assessment Views
        if self.context.get("view") == "assessment":
            return AssessmentGradeSerializer(instance.api_data, context=self.context).data
        else:
            return None
