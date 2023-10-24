""" MFE Serializers related to submissions """
# pylint: disable=abstract-method

from rest_framework.fields import BooleanField
from rest_framework.serializers import (
    IntegerField,
    Serializer,
    CharField,
    ListField,
    SerializerMethodField,
    URLField,
)
from openassessment.xblock.ui_mixins.mfe.serializer_utils import CharListField, NullField


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
    """
    Args:
    * get_learner_submission_data shape

    Returns:
    {
        textResponses
        uploadedFiles
        teamUploadedFiles (Null)
    }
    """
    textResponses = CharListField(allow_empty=True, source='get_text_responses')
    uploadedFiles = SerializerMethodField()
    teamUploadedFiles = NullField(source="*")

    def get_uploadedFiles(self, response):
        result = []
        for index, uploaded_file in enumerate(response.get_file_uploads(generate_urls=True)):
            result.append(SubmissionFileSerializer(({'file': uploaded_file, 'file_index': index})).data)
        return result

    def to_representation(self, instance):
        # Unpack response.
        # This is to keep signature similar between the draft and submitted responses.
        response = instance["response"]
        return super().to_representation(response)


class FileDescriptorSerializer(Serializer):
    fileUrl = URLField(source='file.download_url')
    fileDescription = CharField(source='file.description')
    fileName = CharField(source='file.name')
    fileSize = IntegerField(source='file.size')
    fileIndex = IntegerField(source="file_index")


class TeamFileDescriptorSerializer(Serializer):
    fileUrl = URLField(source='download_url')
    fileDescription = CharField(source='description')
    fileName = CharField(source='name')
    fileSize = IntegerField(source='size')
    uploadedBy = CharField(source="uploaded_by")


class DraftResponseSerializer(Serializer):
    """
    Args:
    * get_learner_submission_data shape

    Returns:
    {
        textResponses
        uploadedFiles
        teamUploadedFiles
    }
    """
    textResponses = SerializerMethodField()
    uploadedFiles = SerializerMethodField()
    teamUploadedFiles = ListField(
        source="team_info.team_uploaded_files",
        allow_empty=True,
        child=TeamFileDescriptorSerializer(),
        default=None,
        required=False
    )

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


class AddFileRequestSerializer(Serializer):
    """
    Input serializer for file/add handler
    """
    fileDescription = CharField(source='description')
    fileName = CharField(source='name')
    fileSize = IntegerField(source='size', min_value=0)
    contentType = CharField()


class FileUploadCallbackRequestSerializer(Serializer):
    """
    Input request serializer for file upload callback handler
    """
    fileIndex = IntegerField(min_value=0)
    success = BooleanField()
