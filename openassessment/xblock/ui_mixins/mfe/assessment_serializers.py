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
    BooleanField,
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


class AssessmentCriterionSerializer(Serializer):
    """
    Serialize assessment criterion values from DB representation to frontend data structure.

    Returns:
    {
        selectedOption: (Int) Order of the selected option
        feedback: (String) Feedback for the selected option
    }
    """
    selectedOption = IntegerField(source="option.order_num")
    feedback = CharField()


class AssessmentDataSerializer(Serializer):
    """
    Serialize assessment data from DB representation to frontend data structure.

    Returns:
    {
        criteria: [ AssessmentCriterionSerializer ]
        overallFeedback: (String / Empty)
    }
    """
    overallFeedback = CharField(source="feedback")
    criteria = AssessmentCriterionSerializer(source="parts", many=True)


class AssessmentStepSerializer(Serializer):
    """
    Assessment step serializer
    """

    stepScore = AssessmentScoreSerializer(source="*")
    assessment = AssessmentDataSerializer(source="*")


class PeerAssessmentsSerializer(Serializer):
    """
    Assessment step serializer for peer step
    """

    stepScore = AssessmentScoreSerializer(source='peer_grade')
    assessments = AssessmentDataSerializer(
        source="scored_assessments",
        many=True,
        allow_empty=True
    )


class UnweightedPeerAssessmentsSerializer(Serializer):
    """
    Assessment step serializer for peer step
    """

    stepScore = NullField(source='*')
    assessments = AssessmentDataSerializer(
        source="unscored_assessments",
        many=True,
        allow_empty=True
    )


class SubmissionFileSerializer(Serializer):
    fileUrl = URLField(source="file_key")
    fileDescription = CharField(source="file_description")
    fileName = CharField(source="file_name")
    fileSize = IntegerField(source="file_size")
    fileIndex = IntegerField(source="file_index")


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

    effectiveAssessmentType = CharField(source="grades_data.effective_assessment_type")
    self = AssessmentStepSerializer(source="self_assessment_data.assessment")
    staff = AssessmentStepSerializer(source="staff_assessment_data.assessment")
    peer = PeerAssessmentsSerializer(source="peer_assessment_data")
    peerUnweighted = UnweightedPeerAssessmentsSerializer(source="peer_assessment_data")


class AssessmentResponseSerializer(Serializer):
    """
    Given we want to load an assessment response,
    gather the appropriate response and serialize.

    Data same shape as Submission, but coming from different sources.

    Args:
    * Response - All assessment responses have the same data

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
        ],
        teamUploadedFiles: Null
    }
    """

    textResponses = SerializerMethodField()
    uploadedFiles = SerializerMethodField()
    teamUploadedFiles = NullField(source="*")

    def __init__(self, instance=None, *args, **kwargs):  # pylint: disable=keyword-arg-before-vararg
        # Very weird workaround to control serialization for None input as data
        # since DRF doesn't run to_representation when None is passed as data
        if instance is None:
            self.fields = {}
        super().__init__(instance, *args, **kwargs)

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


class MfeAssessmentCriterionSerializer(Serializer):
    """
    Frontend's view of rubric criterion values for an assessment

    {
        selectedOption: (Int) Order of the selected option
        feedback: (String / Empty) Feedback for the selected option
    }
    """
    selectedOption = IntegerField()
    feedback = CharField(allow_blank=True, allow_null=True)


class MfeAssessmentDataSerializer(Serializer):
    """
    Frontend's view of Assessment Data.

    criteria: [ MfeAssessmentCriterion ],
    overallFeedback: (String / Empty) Feedback for the Assessment
    """
    criteria = MfeAssessmentCriterionSerializer(many=True)
    overallFeedback = CharField(allow_blank=True)


class AssessmentSubmitRequestSerializer(MfeAssessmentDataSerializer):
    """"
    Serializer for validating request shape and unpacking data for assessment APIs.

    Args: Data in the form
    {
        criteria: [
            // Rubric criterion
            {
                selectedOption: (Int) Order of the selected option
                feedback: (String / Empty) Feedback for the selected option
            }
            ...
        ],
        overallFeedback: (String / Empty)
    }
    """

    continueGrading = BooleanField(required=False, default=False)

    def to_legacy_format(self, xblock):
        """
        Converts given assessment format to format needed for submitting an assessment:

        >>> options_selected = {"clarity": "Very clear", "precision": "Somewhat precise"}
        >>> criterion_feedback = {"clarity": "I thought this essay was very clear."}
        >>> feedback = "Your submission was thrilling."
        """
        options_selected = {}
        criterion_feedback = {}

        for i, criterion_data in enumerate(self.data['criteria']):

            # Look up the name and value for each given rubric selection
            criterion_name = xblock.rubric_criteria[i]['name']
            selected_value = xblock.rubric_criteria[i]['options'][criterion_data['selectedOption']]['name']
            options_selected[criterion_name] = selected_value

            # Attach feedback for the criterion
            criterion_feedback[criterion_name] = criterion_data['feedback']

        return {
            "options_selected": options_selected,
            "criterion_feedback": criterion_feedback,
            "feedback": self.data["overallFeedback"]
        }
