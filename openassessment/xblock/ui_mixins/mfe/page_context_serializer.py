"""
Serializers for ORA's BFF.

These are the response shapes that power the MFE implementation of the ORA UI.
"""
# pylint: disable=abstract-method

from rest_framework.serializers import (
    BooleanField,
    IntegerField,
    Serializer,
    SerializerMethodField,
)
from openassessment.xblock.ui_mixins.mfe.assessment_serializers import (
    AssessmentGradeSerializer,
    AssessmentResponseSerializer,
)
from openassessment.xblock.ui_mixins.mfe.submission_serializers import PageDataSubmissionSerializer
from openassessment.xblock.ui_mixins.mfe.serializer_utils import STEP_NAME_MAPPINGS

from .ora_config_serializer import RubricConfigSerializer


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


class ReceivedGradesSerializer(Serializer):
    """
    Received grades for each of the applicable graded steps
    Returns:
    {
        self: (Assessment score object)
        peer: (Assessment score object)
        staff: (Assessment score object)
    }
    """

    self = AssessmentScoreSerializer(source="grades.self_score")
    peer = AssessmentScoreSerializer(source="grades.peer_score")
    staff = AssessmentScoreSerializer(source="grades.staff_score")

    def to_representation(self, instance):
        """
        Hook output to remove steps that are not part of the assignment.

        Grades are not released for steps until all steps are completed.
        """
        step_names = ["self", "peer", "staff"]

        # NOTE - cache this so we don't update the workflow
        configured_steps = instance.status_details.keys()
        is_done = instance.is_done

        for step in step_names:
            if step not in configured_steps:
                self.fields.pop(step)

        if not is_done:
            return {field: {} for field in self.fields}

        return super().to_representation(instance)


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


class StudentTrainingStepInfoSerializer(StepInfoBaseSerializer):
    """
    Returns:
        {
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

        Returns: List of criterion names and matched selections
        [
            {
                name: (String) Criterion name,
                selection: (String) Option name that should be selected,
            }
        ]
        """
        example = instance.example

        options_selected = []
        for criterion in example["options_selected"]:
            criterion_selection = {
                "name": criterion,
                "selection": example["options_selected"][criterion],
            }
            options_selected.append(criterion_selection)

        return options_selected


class PeerStepInfoSerializer(StepInfoBaseSerializer):
    """
    Returns:
        {
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

    require_context = True

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
        activeStepName: (String) one of ["studentTraining", "peer", "self", "staff"]

        hasReceivedFinalGrade: (Bool) // In effect, is the ORA complete?
        receivedGrades: (Object) Staff grade data, when there is a completed staff grade.
        activeStepInfo: (Object) Specific info for the active step
    }
    """

    activeStepName = SerializerMethodField()
    hasReceivedFinalGrade = BooleanField(source="workflow_data.is_done")
    receivedGrades = ReceivedGradesSerializer(source="workflow_data")
    stepInfo = StepInfoSerializer(source="*")

    def get_activeStepName(self, instance):
        """Return the active step name"""
        if not instance.workflow_data.has_workflow:
            return "submission"
        else:
            return STEP_NAME_MAPPINGS[instance.workflow_data.status]


class PageDataSerializer(Serializer):
    """
    Data for rendering a page in the ORA MFE

    Requires context to differentiate between Assessment and Submission views
    """

    require_context = True

    progress = ProgressSerializer(source="*")
    submission = SerializerMethodField()
    rubric = RubricConfigSerializer(source="*")
    assessment = SerializerMethodField()

    def to_representation(self, instance):
        # Loading workflow status causes a workflow refresh
        # ... limit this to one refresh per page call
        if not self.context.get("step"):
            active_step = instance.workflow_data.status or "submission"
            self.context.update({"step": active_step})

        return super().to_representation(instance)

    def _can_jump_to_step(self, workflow_step, workflow_data, step_name):
        """
        Helper to determine if a student can jump to a specific step:
        1) Student is on that step.
        2) Student has completed that step.

        NOTE that this should probably happen at the handler level, but for
        added safety, check here as well.
        """
        if step_name == workflow_step:
            return True
        step_status = workflow_data.status_details.get(step_name, {})
        return step_status.get("complete", False)

    def get_submission(self, instance):
        """
        we get the user's draft / complete submission.
        """
        # pylint: disable=broad-exception-raised
        # Submission Views
        if self.context.get("view") == "submission":
            learner_page_data_submission_data = instance.get_learner_submission_data()
            return PageDataSubmissionSerializer(learner_page_data_submission_data).data
        # Assessment Views
        elif self.context.get("view") == "assessment":
            # Can't view assessments without completing submission
            if self.context["step"] == "submission":
                raise Exception("Cannot view assessments without having completed submission.")

            # If the student is trying to jump to a step, verify they can
            jump_to_step = self.context.get("jump_to_step")
            workflow_step = self.context["step"]
            if jump_to_step and not self._can_jump_to_step(workflow_step, instance.workflow_data, jump_to_step):
                raise Exception(f"Can't jump to {jump_to_step} step before completion")

            # Go to the current step, or jump to the selected step
            active_step = jump_to_step or workflow_step

            if active_step == "training":
                response = instance.student_training_data.example
            elif active_step == "peer":
                response = instance.peer_assessment_data().get_peer_submission()
            elif active_step in ("self", "staff", "ai", "waiting", "done"):
                response = None
            else:
                raise Exception(f"Bad step name: {active_step}")

            self.context["response"] = response

            return AssessmentResponseSerializer(instance.api_data, context=self.context).data
        else:
            raise Exception("Missing view context for page")

    def get_assessment(self, instance):
        """
         we get an assessment for the current assessment step.
        """
        # Assessment Views
        if self.context.get("view") == "assessment":
            return AssessmentGradeSerializer(instance.api_data, context=self.context).data
        else:
            return None
