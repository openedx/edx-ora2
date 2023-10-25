""" Serializers for legacy UI views and handlers """
# pylint: disable=abstract-method
from rest_framework.serializers import Serializer, CharField, IntegerField, ListField


class SaveFilesDescriptionRequestFileSerializer(Serializer):
    """
    Input serializer for save_files_descriptions handler
    """
    # This reads a bit backwards from other serializers. It's because this is getting data passed in as a
    # kwarg, and then we are calling is_valid and reading from serializer.validated_data.
    # The data passed in has the keys fileName, description and fileSize, and the output has description, name, and size
    description = CharField()
    fileName = CharField(source='name')
    fileSize = IntegerField(source='size')


class SaveFilesDescriptionRequestSerializer(Serializer):
    """
    Input serializer for save_files_descriptions handler
    """
    fileMetadata = ListField(child=SaveFilesDescriptionRequestFileSerializer())
