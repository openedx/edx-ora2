from rest_framework.serializers import (
    Serializer, 
    CharField,
    ListField,
    SerializerMethodField
)

class CharListField(ListField):
    child = CharField()

class OraBlockInfoSerializer(Serializer):
    title = CharField()
    prompts = CharListField()
    base_asset_url = SerializerMethodField(source="*")

    def get_base_asset_url(self, block):
        return block._get_base_url_path_for_course_assets(block.course.id)
