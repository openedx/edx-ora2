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
    editor_type = CharField(source="text_response_editor")
    allow_latex_preview = BooleanField(source="allow_latex")

    def get_enabled(self, block):
        return block.text_response is not None

    def get_required(self, block):
        return block.text_response == "required"


class FileResponseConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    required = SerializerMethodField()
    file_upload_limit = SerializerMethodField()
    allowed_extensions = CharListField(source="get_allowed_file_types_or_preset")
    blocked_extensions = CharListField(source="FILE_EXT_BLACK_LIST")
    allowed_file_type_description = CharField(source="file_upload_type")

    def get_enabled(self, block):
        return block.file_upload_response is not None

    def get_required(self, block):
        return block.file_upload_response == "required"

    def get_file_upload_limit(self, block):
        if not block.allow_multiple_files:
            return 1
        return block.MAX_FILES_COUNT


class TeamsConfigSerializer(Serializer):
    enabled = BooleanField(source="is_team_assignment")
    teamset_name = SerializerMethodField()

    def get_teamset_name(self, block):
        if block.teamset_config is not None:
            return block.teamset_config.name


class SubmissionConfigSerializer(Serializer):
    start = DateTimeField(source="submission_start")
    due = DateTimeField(source="submission_due")

    text_response_config = TextResponseConfigSerializer(source="*")
    file_response_config = FileResponseConfigSerializer(source="*")

    teams_config = TeamsConfigSerializer(source="*")


class RubricFeedbackConfigSerializer(Serializer):
    description = CharField(source="rubric_feedback_prompt")  # is this this field?
    default_text = CharField(source="rubric_feedback_default_text")


class RubricCriterionOptionSerializer(Serializer):
    name = CharField()
    label = CharField()
    points = IntegerField()
    description = CharField(source="explanation")


class RubricCriterionSerializer(Serializer):
    name = CharField(source="label")
    description = CharField(source="prompt")
    feedback_enabled = SerializerMethodField()
    feedback_required = SerializerMethodField()
    options = RubricCriterionOptionSerializer(many=True)

    @staticmethod
    def _feedback(criterion):
        return criterion.get("feedback", "disabled")

    def get_feedback_enabled(self, criterion):
        return self._feedback(criterion) != "disabled"

    def get_feedback_required(self, criterion):
        return self._feedback(criterion) == "required"


class RubricConfigSerializer(Serializer):
    show_during_response = BooleanField(source="show_rubric_during_response")
    feedback_config = RubricFeedbackConfigSerializer(source="*")
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
    min_number_to_grade = IntegerField(source="must_grade")
    min_number_to_be_graded_by = IntegerField(source="must_be_graded_by")
    flexible_grading = BooleanField(source="enable_flexible_grading")


class SelfSettingsSerializer(RequiredMixin, Serializer):
    pass


class StaffSettingsSerializer(RequiredMixin, Serializer):
    pass


class AssessmentStepsSettingsSerializer(Serializer):
    training_step = SerializerMethodField(label="training")
    peer_step = SerializerMethodField(label="peer")
    self_step = SerializerMethodField(label="self")
    staff_step = SerializerMethodField(label="staff")

    def _get_step(self, instance, step_name):
        """Get the assessment step config for a given step_name"""
        for step in instance.rubric_assessments:
            if step["name"] == step_name:
                return step
        return None

    def get_training_step(self, instance):
        """Get the training step configuration"""
        training_step = self._get_step(instance, "student-training")
        return TrainingSettingsSerializer(training_step).data or {}

    def get_peer_step(self, instance):
        """Get the peer step configuration"""
        peer_step = self._get_step(instance, "peer-assessment")
        return PeerSettingsSerializer(peer_step).data or {}

    def get_self_step(self, instance):
        """Get the self step configuration"""
        self_step = self._get_step(instance, "self-assessment")
        return SelfSettingsSerializer(self_step).data or {}

    def get_staff_step(self, instance):
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
    number_to_show = IntegerField(source="leaderboard_show")

    def get_enabled(self, block):
        return block.leaderboard_show > 0


class OraBlockInfoSerializer(Serializer):
    """
    Main serializer for statically-defined ORA Block information
    """

    title = CharField()
    prompts = SerializerMethodField(source="*")
    base_asset_url = SerializerMethodField(source="*")

    submission_config = SubmissionConfigSerializer(source="*")
    assessment_steps = AssessmentStepsSerializer(source="*")
    rubric_config = RubricConfigSerializer(source="*")
    leaderboard = LeaderboardConfigSerializer(source="*")

    def get_base_asset_url(self, block):
        return block._get_base_url_path_for_course_assets(block.course.id)

    def get_prompts(self, block):
        return [prompt["description"] for prompt in block.prompts]
