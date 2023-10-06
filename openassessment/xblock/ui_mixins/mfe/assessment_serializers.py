"""
Serializer for assessments
"""
# pylint: disable=abstract-method

from rest_framework.serializers import (
    CharField,
    IntegerField,
    SerializerMethodField,
    URLField,
    Serializer,
)
from openassessment.xblock.ui_mixins.mfe.serializer_utils import NullField


class AssessmentScoreSerializer(Serializer):
    """
    Returns:
    {
        earned: (Int) How many points were you awarded by peers?
        possible: (Int) What was the max possible grade?
    }
    """

    earned = IntegerField(source="points_earned", required=False)
    possible = IntegerField(source="points_possible", required=False)


class AssessmentDataSerializer(Serializer):
    """
    Assessment data serializer
    """
    optionsSelected = SerializerMethodField()
    criterionFeedback = SerializerMethodField()
    overallFeedback = SerializerMethodField()

    def get_optionsSelected(self, instance):
        result = {}
        for part in instance['parts']:
            result[part['option']['name']] = part['option']['label']
        return result

    def get_overallFeedback(self, instance):
        return instance['feedback']

    def get_criterionFeedback(self, instance):
        result = {}
        for part in instance['parts']:
            result[part['criterion']['name']] = part['feedback']
        return result


class AssessmentStepSerializer(Serializer):
    """
    Assessment step serializer
    """
    stepScore = AssessmentScoreSerializer(source="*")
    assessment = AssessmentDataSerializer(source="*")


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
                "file_key": file_key,
                "file_description": instance["answer"]["files_descriptions"][i],
                "file_name": instance["answer"]["files_names"][i],
                "file_size": instance["answer"]["files_sizes"][i],
                "file_index": i,
            }

            # Don't serialize deleted / missing files
            if not file_data["file_name"] and not file_data["file_description"]:
                continue

            files.append(file_data)

        return [SubmissionFileSerializer(file).data for file in files]


class AssessmentGradeSerializer(Serializer):
    """
    Given we want to load an assessment response,
    gather the appropriate response and serialize.

    Data same shape as Submission, but coming from different sources.

    Returns:
    {
        effectiveAssessmentType: String
        self: AssessmentStepSerializer
        staff: AssessmentStepSerializer
        peers: AssessmentStepSerializer[]
    }
    """
    effectiveAssessmentType = SerializerMethodField()
    self = AssessmentStepSerializer(source="self_assessment_data.assessment")
    staff = AssessmentStepSerializer(source="staff_assessment_data.assessment")
    peers = AssessmentStepSerializer(source="peer_assessment_data.assessments", many=True)

    def get_effectiveAssessmentType(self, instance):  # pylint: disable=unused-argument
        """
        Get effective assessment type
        """
        return self.context["step"]


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
    """

    hasSubmitted = NullField(source="*")
    hasCancelled = NullField(source="*")
    hasReceivedGrade = NullField(source="*")
    teamInfo = NullField(source="*")

    response = SerializerMethodField()

    def get_response(self, instance):  # pylint: disable=unused-argument
        # Response is passed in through context, so we don't have to fetch it
        # in multiple locations.
        response = self.context.get("response")
        if not response:
            return {}
        return SubmittedResponseSerializer(response).data
