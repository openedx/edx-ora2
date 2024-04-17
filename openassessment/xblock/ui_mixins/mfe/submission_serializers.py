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


class SubmissionFileSerializer(Serializer):
    """
    Files for a submitted response, different format from draft response.

    Args: {
        "file": (Object),
        "file_index": (Int),
    }
    """
    fileUrl = URLField(source='file.url')
    fileDescription = CharField(source='file.description')
    fileName = CharField(source='file.name')
    fileSize = IntegerField(source='file.size')
    fileIndex = IntegerField(source="file_index")


class SubmissionSerializer(Serializer):
    """
    Serialize a submitted response, different format from draft responses.

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
            # Don't serialize deleted / missing files
            if uploaded_file.url is None:
                continue
            result.append(SubmissionFileSerializer(({'file': uploaded_file, 'file_index': index})).data)
        return result

    def to_representation(self, instance):
        # Unpack response.
        # This is to keep signature similar between the draft and submitted responses.
        response = instance["response"]
        return super().to_representation(response)


class FileDescriptorSerializer(Serializer):
    """
    Files uploaded for a draft response, different format from submitted responses.

    Args: {
        file: (Object),
        file_index: (Int),
    }
    """
    fileUrl = URLField(source='file.download_url')
    fileDescription = CharField(source='file.description')
    fileName = CharField(source='file.name')
    fileSize = IntegerField(source='file.size')
    fileIndex = IntegerField(source="file_index")


class TeamFileDescriptorSerializer(Serializer):
    """
    Files uploaded by team members for a draft response, different format from submitted responses.
    """
    fileUrl = URLField(source='download_url')
    fileDescription = CharField(source='description')
    fileName = CharField(source='name')
    fileSize = IntegerField(source='size')
    uploadedBy = CharField(source="uploaded_by")


class DraftResponseSerializer(Serializer):
    """
    Serialize a draft response, a different format from submitted responses.

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
            # hide deleted files from output
            if uploaded_file["download_url"] is not None:
                result.append(FileDescriptorSerializer(({'file': uploaded_file, 'file_index': index})).data)
        return result


class AddFileRequestSerializer(Serializer):
    """
    Input serializer for file/add handler
    """
    fileDescription = CharField(source='description')
    fileName = CharField(source='name')
    fileSize = IntegerField(source='size', min_value=0)
    contentType = CharField(allow_blank=True)


class FileUploadCallbackRequestSerializer(Serializer):
    """
    Input request serializer for file upload callback handler
    """
    fileIndex = IntegerField(min_value=0)
    success = BooleanField()
