from rest_framework.serializers import (
    BooleanField,
    DateTimeField,
    Serializer,
    CharField,
    ListField,
    SerializerMethodField
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

class SubmissionConfigSerializer(Serializer):
    start = DateTimeField(source="submission_start")
    due = DateTimeField(source="submission_due")

    text_response_config = TextResponseConfigSerializer(source='*')
    file_response_config = FileResponseConfigSerializer(source='*')

    teams_config = TeamsConfigSerializer(source="*")

class OraBlockInfoSerializer(Serializer):
    """
    Main serializer for statically-defined ORA Block information
    """

    title = CharField()
    prompts = SerializerMethodField(source="*")
    base_asset_url = SerializerMethodField(source="*")

    submission_config = SubmissionConfigSerializer(source="*")

    def get_base_asset_url(self, block):
        return block._get_base_url_path_for_course_assets(block.course.id)

    def get_prompts(self, block):
        return [prompt["description"] for prompt in block.prompts]
