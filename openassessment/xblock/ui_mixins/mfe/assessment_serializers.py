"""
Serializer for assessments
"""
# pylint: disable=abstract-method

from rest_framework.fields import (
    CharField,
    IntegerField,
    SerializerMethodField,
    URLField,
)
from rest_framework.serializers import Serializer

from openassessment.xblock.ui_mixins.mfe.serializer_utils import NullField


class SubmissionFileSerializer(Serializer):
    fileUrl = URLField(source="file_key")
    fileDescription = CharField(source="file_description")
    fileName = CharField(source="file_name")
    fileSize = IntegerField(source="file_size")
    fileIndex = IntegerField(source="file_index")


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
        answer_text_parts = instance["answer"].get("parts", [])
        return [part["text"] for part in answer_text_parts]

    def get_uploadedFiles(self, instance):
        # coerce to a similar shape for easier serialization
        files = []

        if not instance["answer"].get("file_keys"):
            return None

        for i, file_key in enumerate(instance["answer"]["file_keys"]):
            file_data = {
                "file_url": file_key,
                "file_description": instance["answer"]["files_descriptions"][i],
                "file_name": instance["answer"]["files_names"][i],
                "file_size": instance["answer"]["files_sizes"][i],
            }

        return [SubmissionFileSerializer(file).data for file in files]


class AssessmentResponseSerializer(Serializer):
    """
    Given we want to load an assessment response,
    gather the appropriate response and serialize.

    Data same shape as Submission, but coming from different sources.

    Returns:
    {
        // Null for Assessments
        hasSubmitted: None
        hasCancelled: None
        hasReceivedGrade: None
        teamInfo: None

        // The actual response to view
        response: (Object)
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
    }
    """

    hasSubmitted = NullField(source="*")
    hasCancelled = NullField(source="*")
    hasReceivedGrade = NullField(source="*")
    teamInfo = NullField(source="*")

    response = SerializerMethodField()

    def get_response(self, instance):
        active_step = self.context.get("step")

        if active_step == "submission":
            raise Exception(
                "Cannot view assessments without having completed submission."
            )
        elif active_step == "training":
            response = instance.student_training_data.example
            return SubmittedResponseSerializer(response).data
        elif active_step == "peer":
            response = instance.peer_assessment_data().get_peer_submission()
            if not response:
                return {}
            return SubmittedResponseSerializer(response).data
        elif active_step in ("staff", "waiting", "done"):
            return {}
        else:
            raise Exception(f"Bad step name: {active_step}")
