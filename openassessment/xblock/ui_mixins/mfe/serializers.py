"""
Serializers for ORA's BFF.

These are the response shapes that power the MFE implementation of the ORA UI.
"""
# pylint: disable=abstract-method

from rest_framework.serializers import (
    BooleanField,
    DateTimeField,
    IntegerField,
    Serializer,
    CharField,
    ListField,
    SerializerMethodField,
)


class CharListField(ListField):
    child = CharField()


class IsRequiredField(BooleanField):
    """
    Utility for checking if a field is "required" to reduce repeated code.
    """

    def to_representation(self, value):
        return value == "required"


class TextResponseConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    required = IsRequiredField(source="text_response")
    editorType = CharField(source="text_response_editor")
    allowLatexPreview = BooleanField(source="allow_latex")

    def get_enabled(self, block):
        return block.text_response is not None


class FileResponseConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    required = IsRequiredField(source="file_upload_response")
    fileUploadLimit = SerializerMethodField()
    allowedExtensions = CharListField(source="get_allowed_file_types_or_preset")
    blockedExtensions = CharListField(source="FILE_EXT_BLACK_LIST")
    fileTypeDescription = CharField(source="file_upload_type")

    def get_enabled(self, block):
        return block.file_upload_response is not None

    def get_fileUploadLimit(self, block):
        if not block.allow_multiple_files:
            return 1
        return block.MAX_FILES_COUNT


class TeamsConfigSerializer(Serializer):
    enabled = BooleanField(source="is_team_assignment")
    teamsetName = SerializerMethodField()

    def get_teamsetName(self, block):
        if block.teamset_config is not None:
            return block.teamset_config.name
        return None


class SubmissionConfigSerializer(Serializer):
    startDatetime = DateTimeField(source="submission_start")
    endDatetime = DateTimeField(source="submission_due")

    textResponseConfig = TextResponseConfigSerializer(source="*")
    fileResponseConfig = FileResponseConfigSerializer(source="*")

    teamsConfig = TeamsConfigSerializer(source="*")


class RubricFeedbackConfigSerializer(Serializer):
    description = CharField(source="rubric_feedback_prompt")  # is this this field?
    defaultText = CharField(source="rubric_feedback_default_text")


class RubricCriterionOptionSerializer(Serializer):
    name = CharField()
    label = CharField()
    points = IntegerField()
    description = CharField(source="explanation")


class RubricCriterionSerializer(Serializer):
    name = CharField(source="label")
    description = CharField(source="prompt")
    feedbackEnabled = SerializerMethodField()
    feedbackRequired = IsRequiredField(source="feedback")
    options = RubricCriterionOptionSerializer(many=True)

    @staticmethod
    def _feedback(criterion):
        # Feedback is disabled as a default
        return criterion.get("feedback", "disabled")

    def get_feedbackEnabled(self, criterion):
        # Feedback can be specified as optional or required
        return self._feedback(criterion) != "disabled"


class RubricConfigSerializer(Serializer):
    showDuringResponse = BooleanField(source="show_rubric_during_response")
    feedbackConfig = RubricFeedbackConfigSerializer(source="*")
    criteria = RubricCriterionSerializer(
        many=True, source="rubric_criteria_with_labels"
    )


class SelfSettingsSerializer(Serializer):
    required = BooleanField(default=True)

    startTime = DateTimeField(source="start")
    endTime = DateTimeField(source="due")


class PeerSettingsSerializer(Serializer):
    required = BooleanField(default=True)

    startTime = DateTimeField(source="start")
    endTime = DateTimeField(source="due")

    minNumberToGrade = IntegerField(source="must_grade")
    minNumberToBeGradedBy = IntegerField(source="must_be_graded_by")

    enableFlexibleGrading = BooleanField(
        source="enable_flexible_grading", required=False
    )


class AssessmentStepSettingsSerializer(Serializer):
    """
    Generic Assessments step, where we just need to know if the step is
    required given the ora.rubric_assessments source.
    """

    required = BooleanField(default=True)

    def _get_step(self, rubric_assessments, step_name):
        """Get the assessment step config for a given step_name"""
        for step in rubric_assessments:
            if step["name"] == step_name:
                return step
        return None

    def __init__(self, *args, **kwargs):
        self.step_name = kwargs.pop("step_name")
        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        assessment_step = self._get_step(instance, self.step_name)

        # Special handling for the peer step which includes extra fields
        if assessment_step and self.step_name == "peer-assessment":
            return PeerSettingsSerializer(assessment_step).data
        elif assessment_step and self.step_name == "self-assessment":
            return SelfSettingsSerializer(assessment_step).data

        # If we didn't find a step, it is not required
        if assessment_step is None:
            assessment_step = {"required": False}

        return super().to_representation(assessment_step)


class AssessmentStepsSettingsSerializer(Serializer):
    training = AssessmentStepSettingsSerializer(
        step_name="student-training", source="rubric_assessments"
    )
    peer = AssessmentStepSettingsSerializer(
        step_name="peer-assessment", source="rubric_assessments"
    )
    # Workaround to allow reserved keyword in serializer key
    vars()["self"] = AssessmentStepSettingsSerializer(
        step_name="self-assessment", source="rubric_assessments"
    )
    staff = AssessmentStepSettingsSerializer(
        step_name="staff-assessment", source="rubric_assessments"
    )


class AssessmentStepsSerializer(Serializer):
    order = SerializerMethodField()
    settings = AssessmentStepsSettingsSerializer(source="*")

    def get_order(self, block):
        return [step["name"] for step in block.rubric_assessments]


class LeaderboardConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    numberOfEntries = IntegerField(source="leaderboard_show")

    def get_enabled(self, block):
        return block.leaderboard_show > 0


class OraBlockInfoSerializer(Serializer):
    """
    Main serializer for statically-defined ORA Block information
    """

    title = CharField()
    prompts = SerializerMethodField(source="*")
    baseAssetUrl = SerializerMethodField(source="*")

    submissionConfig = SubmissionConfigSerializer(source="*")
    assessmentSteps = AssessmentStepsSerializer(source="*")
    rubricConfig = RubricConfigSerializer(source="*")
    leaderboardConfig = LeaderboardConfigSerializer(source="*")

    def get_baseAssetUrl(self, block):
        # pylint: disable=protected-access
        return block.get_base_url_path_for_course_assets(
            block.course.id
        )

    def get_prompts(self, block):
        return [prompt["description"] for prompt in block.prompts]
