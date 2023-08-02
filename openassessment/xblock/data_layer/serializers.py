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


class TextResponseConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    required = SerializerMethodField()
    editorType = CharField(source="text_response_editor")
    allowLatexPreview = BooleanField(source="allow_latex")

    def get_enabled(self, block):
        return block.text_response is not None

    def get_required(self, block):
        return block.text_response == "required"


class FileResponseConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    required = SerializerMethodField()
    fileUploadLimit = SerializerMethodField()
    allowedExtensions = CharListField(source="get_allowed_file_types_or_preset")
    blockedExtensions = CharListField(source="FILE_EXT_BLACK_LIST")
    allowedFileTypeDescription = CharField(source="file_upload_type")

    def get_enabled(self, block):
        return block.file_upload_response is not None

    def get_required(self, block):
        return block.file_upload_response == "required"

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


class SubmissionConfigSerializer(Serializer):
    start = DateTimeField(source="submission_start")
    due = DateTimeField(source="submission_due")

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
    feedbackRequired = SerializerMethodField()
    options = RubricCriterionOptionSerializer(many=True)

    @staticmethod
    def _feedback(criterion):
        return criterion.get("feedback", "disabled")

    def get_feedbackEnabled(self, criterion):
        return self._feedback(criterion) != "disabled"

    def get_feedbackRequired(self, criterion):
        return self._feedback(criterion) == "required"


class RubricConfigSerializer(Serializer):
    showDuringResponse = BooleanField(source="show_rubric_during_response")
    feedbackConfig = RubricFeedbackConfigSerializer(source="*")
    criteria = RubricCriterionSerializer(
        many=True, source="rubric_criteria_with_labels"
    )


class RequiredMixin(Serializer):
    required = BooleanField(default=True)


class StartEndMixin(Serializer):
    start = DateTimeField()
    due = DateTimeField()


class TrainingSettingsSerializer(RequiredMixin, Serializer):
    pass


class PeerSettingsSerializer(RequiredMixin, StartEndMixin, Serializer):
    minNumberToGrade = IntegerField(source="must_grade")
    minNumberToBeGradedBy = IntegerField(source="must_be_graded_by")
    flexibleGrading = BooleanField(source="enable_flexible_grading", required=False)


class SelfSettingsSerializer(RequiredMixin, Serializer):
    pass


class StaffSettingsSerializer(RequiredMixin, Serializer):
    pass


class AssessmentStepsSettingsSerializer(Serializer):
    trainingStep = SerializerMethodField()
    peerStep = SerializerMethodField()
    selfStep = SerializerMethodField()
    staffStep = SerializerMethodField()

    def _get_step(self, instance, step_name):
        """Get the assessment step config for a given step_name"""
        for step in instance.rubric_assessments:
            if step["name"] == step_name:
                return step
        return None

    def get_trainingStep(self, instance):
        """Get the training step configuration"""
        training_step = self._get_step(instance, "student-training")
        return TrainingSettingsSerializer(training_step).data or {}

    def get_peerStep(self, instance):
        """Get the peer step configuration"""
        peer_step = self._get_step(instance, "peer-assessment")
        return PeerSettingsSerializer(peer_step).data or {}

    def get_selfStep(self, instance):
        """Get the self step configuration"""
        self_step = self._get_step(instance, "self-assessment")
        return SelfSettingsSerializer(self_step).data or {}

    def get_staffStep(self, instance):
        """Get the staff step configuration"""
        staff_step = self._get_step(instance, "staff-assessment")
        return StaffSettingsSerializer(staff_step).data or {}


class AssessmentStepsSerializer(Serializer):
    order = SerializerMethodField()
    settings = AssessmentStepsSettingsSerializer(source="*")

    def get_order(self, block):
        return [step["name"] for step in block.rubric_assessments]


class LeaderboardConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    numberToShow = IntegerField(source="leaderboard_show")

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
    leaderboard = LeaderboardConfigSerializer(source="*")

    def get_baseAssetUrl(self, block):
        return block._get_base_url_path_for_course_assets(block.course.id)

    def get_prompts(self, block):
        return [prompt["description"] for prompt in block.prompts]
