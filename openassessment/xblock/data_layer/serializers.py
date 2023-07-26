from rest_framework.serializers import (
    Serializer, 
    BooleanField, 
    CharField,
    ListField,
    URLField,
    DateTimeField,
    IntegerField,
    SerializerMethodField
)

class CharListField(ListField):
    child = CharField()

class ORABlockSerializer(Serializer):
    title = CharField()
    prompts = CharListField()
    base_asset_url = SerializerMethodField(source="*")
    submission_config = SubmissionConfigSerializer(source="*")
    teams_config = TeamsConfigSerializer(source="*")
    assessment_steps = AssessmentStepsSerializer(source="*")
    rubric_config = RubricConfigSerializer(source="*")
    leaderboard_config = LeaderboardConfigSerializer(source="*")
    
    def get_base_asset_url(self, block):
        return block._get_base_url_path_for_course_assets(block.course_id)

class SubmissionConfigSerializer(Serializer):
    start = DateTimeField(source="submission_start")
    due = DateTimeField(source="submission_due")

    text_response_config = TextResponseConfigSerializer(source='*')
    file_response_config = FileResponseConfigSerializer(source='*')

class TextResponseConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    required = SerializerMethodField()
    editor_type = CharField(source="text_response_editor")
    allow_latex_preview = BooleanField(source="allow_latex")
    
    def get_enabled(self, block):
        return block.text_response is not None

    def get_required(self, block):
        return block.text_response == 'required'

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
        return block.file_upload_response == 'required'
    
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

# It's so unclear to me how the block stores this stuff.
# What's the best way to handle all this? I feel like there's an
# obvious solution but I can't see it


# editor_assessments_order:	['student-training', 'self-assessment', 'peer-assessment', 'staff-assessment']
# rubric_assessments:  [{'examples': [{'answer': ['Replace this text with your own sample response for this assignment. Then, under Response Score to the right, select an option for each criterion. Learners practice performing peer assessments by assessing this response and comparing the options that they select in the rubric with the options that you specified.'], 'options_selected': [{'criterion': 'Ideas', 'option': 'Fair'}, {'criterion': 'Content', 'option': 'Good'}]}, {'answer': ['Replace this text with another sample response, and then specify the options that you would select for this response.'], 'options_selected': [{'criterion': 'Ideas', 'option': 'Poor'}, {'criterion': 'Content', 'option': 'Good'}]}], 'name': 'student-training', 'start': None, 'enable_flexible_grading': False, 'due': None}, {'start': '2001-01-01T00:00:00+00:00', 'due': '2029-01-01T00:00:00+00:00', 'name': 'self-assessment', 'enable_flexible_grading': False}, {'must_grade': 5, 'must_be_graded_by': 3, 'enable_flexible_grading': False, 'start': '2001-01-01T00:00:00+00:00', 'due': '2029-01-01T00:00:00+00:00', 'name': 'peer-assessment'}, {'required': True, 'name': 'staff-assessment', 'start': None, 'enable_flexible_grading': False, 'due': None}]


class AssessmentStepsSerializer(Serializer):
    order = CharListField()
    settings = AssessmentStepsSettingsSerializer(source="*")

class AssessmentStepsSettingsSerializer(Serializer):
    peer = PeerSettingsSerializer()
    staff = StaffSettingsSerializer()
    self = SelfSettingsSerializer()
    training = TrainingSettingsSerializer()

class RequiredMixin:
    required = BooleanField()

class StartEndMixin:
    start = DateTimeField()
    due = DateTimeField()

class PeerSettingsSerializer(RequiredMixin, StartEndMixin, Serializer):
    min_number_to_grade = IntegerField()
    min_number_to_be_graded_by = IntegerField()
    flexible_grading = BooleanField() 

class StaffSettingsSerializer(RequiredMixin, Serializer):
    pass

class SelfSettingsSerializer(RequiredMixin, StartEndMixin, Serializer):
    pass

class TrainingSettingsSerializer(RequiredMixin, Serializer):
    pass

class RubricConfigSerializer(Serializer):
    show_during_response = BooleanField(source="show_rubric_during_response")
    feedback_config = RubricFeedbackConfigSerializer(source="*")
    criteria = RubricCriterionSerializer(many=True, source="rubric_criteria_with_labels")

class RubricFeedbackConfigSerializer(Serializer):
    description = CharField(source="rubric_feedback_prompt") #is this this field?
    default_text = CharField(source="rubric_feedback_default_text")

class RubricCriterionSerializer(Serializer):
    name = CharField(source="label")
    description = CharField(source="prompt")
    feedback_enabled = SerializerMethodField()
    feedback_required = SerializerMethodField()
    options = RubricCriterionOptionSerializer(many=True, source="options")
    
    @staticmethod
    def _feedback(criterion):
        return criterion.get('feedback', 'disabled')
    
    def get_feedback_enabled(self, criterion):
        return self._feedback(criterion) != 'disabled'
    
    def get_feedback_required(self, criterion):
        return self._feedback(criterion) == 'required'

class RubricCriterionOptionSerializer(Serializer):
    name = CharField()
    label = CharField()
    points = IntegerField()
    description = CharField(source="explanation")

class LeaderboardConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    number_to_show = IntegerField(source="leaderboard_show")

    def get_enabled(self, block):
        return block.leaderboard_show > 0