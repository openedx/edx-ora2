""" MFE Serializers related to submissions """
# pylint: disable=abstract-method

from rest_framework.serializers import (
    BooleanField,
    IntegerField,
    Serializer,
    CharField,
    ListField,
    SerializerMethodField,
    URLField,
)
from openassessment.xblock.ui_mixins.mfe.serializer_utils import CharListField


class FileIndexListField(ListField):
    def to_representation(self, data):
        return [
            self.child.to_representation({'item': item, 'file_index': i}) if item is not None else None
            for i, item in enumerate(data)
        ]


class SubmissionFileSerializer(Serializer):
    fileUrl = URLField(source='file.url')
    fileDescription = CharField(source='file.description')
    fileName = CharField(source='file.name')
    fileSize = IntegerField(source='file.size')
    fileIndex = IntegerField(source="file_index")


class SubmissionSerializer(Serializer):
    textResponses = CharListField(allow_empty=True, source='get_text_responses')
    uploadedFiles = SerializerMethodField()

    def get_uploadedFiles(self, submission):
        result = []
        for index, uploaded_file in enumerate(submission.get_file_uploads(generate_urls=True)):
            result.append(SubmissionFileSerializer(({'file': uploaded_file, 'file_index': index})).data)
        return result


class FileDescriptorSerializer(Serializer):
    fileUrl = URLField(source='file.download_url')
    fileDescription = CharField(source='file.description')
    fileName = CharField(source='file.name')
    fileSize = IntegerField(source='file.size')
    fileIndex = IntegerField(source="file_index")


class InProgressResponseSerializer(Serializer):
    textResponses = SerializerMethodField()
    uploadedFiles = SerializerMethodField()

    def get_textResponses(self, data):
        return [
            part['text']
            for part in data['response']['answer']['parts']
        ]

    def get_uploadedFiles(self, data):
        result = []
        for index, uploaded_file in enumerate(data['file_data']):
            result.append(FileDescriptorSerializer(({'file': uploaded_file, 'file_index': index})).data)
        return result


class PageDataSubmissionSerializer(Serializer):
    """
    Main serializer for learner submission status / info
    """
    response = SerializerMethodField(source="*")

    def get_response(self, data):
        # The source data is different if we have an in-progress response vs a submitted response
        if data['workflow']['has_submitted']:
            return SubmissionSerializer(data['response']).data
        return InProgressResponseSerializer(data).data


class AddFileRequestSerializer(Serializer):
    """
    Input serializer for file/add handler
    """
    fileDescription = CharField(source='description')
    fileName = CharField(source='name')
    fileSize = IntegerField(source='size', min_value=0)
    contentType = CharField()
