"""
Submission-related serializers for ORA's BFF.

These are the response shapes that power the MFE implementation of the ORA UI.
"""
# pylint: disable=abstract-method

from rest_framework.fields import (
    BooleanField,
    CharField,
    IntegerField,
    ListField,
    URLField,
)
from rest_framework.serializers import Serializer, SerializerMethodField

from openassessment.xblock.ui_mixins.mfe.serializer_utils import CharListField


class FileIndexListField(ListField):
    """
    A list of file data, each with a corresponding index number
    """

    def to_representation(self, data):
        return [
            self.child.to_representation({"item": item, "file_index": i})
            if item is not None
            else None
            for i, item in enumerate(data)
        ]


class SubmissionFileSerializer(Serializer):
    fileUrl = URLField(source="item.url")
    fileDescription = CharField(source="item.description")
    fileName = CharField(source="item.name")
    fileSize = IntegerField(source="item.size")
    fileIndex = IntegerField(source="file_index")


class FileDescriptorSerializer(Serializer):
    fileUrl = URLField(source="item.download_url")
    fileDescription = CharField(source="item.description")
    fileName = CharField(source="item.name")
    fileSize = IntegerField(source="item.size")
    fileIndex = IntegerField(source="file_index")


class TeamFileDescriptorSerializer(Serializer):
    fileUrl = URLField(source="download_url")
    fileDescription = CharField(source="description")
    fileName = CharField(source="name")
    fileSize = IntegerField(source="size")
    uploadedBy = CharField(source="uploaded_by")


class TeamInfoSerializer(Serializer):
    teamName = CharField(source="team_info.team_name", allow_null=True)
    teamUsernames = CharListField(source="team_info.team_usernames", allow_null=True)
    previousTeamName = CharField(source="team_info.previous_team_name", allow_null=True)
    hasSubmitted = BooleanField(source="has_team_submitted")
    teamUploadedFiles = ListField(
        source="files.uploaded_files.team_file_urls",
        allow_empty=True,
        child=TeamFileDescriptorSerializer(),
        required=False,
    )

    def to_representation(self, instance):
        if not instance.is_team_assignment:
            return None

        # After submission, we don't care about this field.
        # ... in fact, it is sort of misleading. Null it out in this case.
        if instance.has_submitted:
            self.fields["teamUploadedFiles"].to_representation = lambda _: None

        return super().to_representation(instance)


class DraftResponseSerializer(Serializer):
    """
    Data for an unsubmitted / drat response

    Returns:
    {
        textResponses: (Array [String])
        [
            (String) Matched with prompts
        ],
        uploadedFiles: (Array [Object])
        [
            {
                fileUrl: (URL) S3 location
                fileDescription: (String)
                fileName: (String)
                fileSize: (Bytes?)
                fileIndex: (Integer, positive)
            }
        ]
    }
    """

    textResponses = SerializerMethodField()
    uploadedFiles = FileIndexListField(
        allow_empty=True,
        source="files.uploaded_files.file_urls",
        child=FileDescriptorSerializer(),
    )

    def get_textResponses(self, instance):
        """
        Get response from saved response format
        {"answer": {"text": ""}}
        """
        if not instance.response_config["text_response"]:
            return None

        # An empty response has a different format from a saved response
        # Return empty single text part if not yet saved.
        empty_text_parts = [{"text": ""}]
        saved_text_parts = instance.saved_response["answer"].get(
            "parts", empty_text_parts
        )
        return [part["text"] for part in saved_text_parts]


class SubmittedResponseSerializer(Serializer):
    """
    Data for a submitted response

    Returns:
    {
        textResponses: (Array [String])
        [
            (String) Matched with prompts
        ],
        uploaded_files: (Array [Object])
        [
            {
                fileUrl: (URL) S3 location
                fileDescription: (String)
                fileName: (String)
                fileSize: (Bytes?)
                fileIndex: (Integer, positive)
            }
        ]
    }
    """

    textResponses = SerializerMethodField()
    uploadedFiles = SerializerMethodField()

    def get_textResponses(self, instance):
        # An empty response has a different format from a saved response
        # Return empty single text part if not yet saved.
        empty_text_parts = [{"text": ""}]
        answer_text_parts = instance["answer"].get("parts", empty_text_parts)
        return [part["text"] for part in answer_text_parts]

    def get_uploadedFiles(self, instance):
        # coerce to a similar shape for easier serialization
        files = []

        for i, file_key in enumerate(instance["answer"]["file_keys"]):
            file_data = {
                "url": file_key,
                "description": instance["answer"]["files_descriptions"][i],
                "name": instance["answer"]["files_names"][i],
                "size": instance["answer"]["files_sizes"][i],
            }
            files.append({"item": file_data, "file_index": i})

        return [SubmissionFileSerializer(file).data for file in files]


class SubmissionSerializer(Serializer):
    """
    Main entrypoint for returning response data. Can be either a(n):
    1) Empty response (user hasn't started drafting a response)
    2) Draft response (user has started, but not submitted, a response)
    3) Submitted response (user has submitted a response)
    4) Cancelled response (user submitted and response was cancelled)

    Returns:
    {
        // Status info
        hasSubmitted: (Bool)
        hasCancelled: (Bool)
        hasReceivedGrade: (Bool)

        // Team info needed for team responses
        // Empty object for individual submissions
        teamInfo: (Object)

        // The actual response to view
        response: (Object)
    }
    """

    hasSubmitted = BooleanField(source="has_submitted")
    hasCancelled = BooleanField(source="has_been_cancelled")
    hasReceivedGrade = BooleanField(source="has_received_final_grade")

    teamInfo = TeamInfoSerializer(source="*")
    response = SerializerMethodField()

    def get_response(self, instance):
        # Response has been cancelled
        if instance.has_been_cancelled:
            return {}

        # Student has not submitted - return draft response
        if not instance.has_submitted:
            return DraftResponseSerializer(instance).data

        # Student has submitted - return submitted response
        return SubmittedResponseSerializer(instance.student_submission).data
