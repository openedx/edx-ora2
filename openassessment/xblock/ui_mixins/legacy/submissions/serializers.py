""" Serializers for legacy UI views and handlers """
# pylint: disable=abstract-method
from rest_framework.serializers import Serializer, CharField, IntegerField, ListField


class SaveFilesDescriptionRequestFileSerializer(Serializer):
    """
    Input serializer for save_files_descriptions handler
    """
    description = CharField()
    fileName = CharField(source='name')
    fileSize = IntegerField(source='size')


class SaveFilesDescriptionRequestSerializer(Serializer):
    """
    Input serializer for save_files_descriptions handler
    """
    fileMetadata = ListField(child=SaveFilesDescriptionRequestFileSerializer())
