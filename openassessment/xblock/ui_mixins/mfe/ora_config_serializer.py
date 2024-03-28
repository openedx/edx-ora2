"""
Serializers for ORA's BFF.

These are the response shapes that power the MFE implementation of the ORA UI.
"""
# pylint: disable=abstract-method
from rest_framework.serializers import (
    BooleanField,
    DateTimeField,
    IntegerField,
    Serializer,
    CharField,
    SerializerMethodField,
)

from openassessment.assessment.api.peer import PeerGradingStrategy
from openassessment.xblock.utils.resolve_dates import DISTANT_FUTURE, DISTANT_PAST
from openassessment.xblock.apis.workflow_api import WorkflowStep

from openassessment.xblock.ui_mixins.mfe.serializer_utils import (
    STEP_NAME_MAPPINGS,
    CharListField,
    IsRequiredField,
)


class TextResponseConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    required = IsRequiredField(source="text_response")
    editorType = CharField(source="text_response_editor")
    allowLatexPreview = BooleanField(source="allow_latex")

    def get_enabled(self, block):
        return block.text_response is not None


class FileResponseConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    required = IsRequiredField(source="file_upload_response")
    fileUploadLimit = SerializerMethodField()
    allowedExtensions = CharListField(source="get_allowed_file_types_or_preset")
    blockedExtensions = CharListField(source="FILE_EXT_BLACK_LIST")
    fileTypeDescription = CharField(source="file_upload_type")
    maxFileSize = IntegerField(default=524_288_000)  # 500 MB. See AU-1602

    def get_enabled(self, block):
        return block.file_upload_response is not None

    def get_fileUploadLimit(self, block):
        if not block.allow_multiple_files:
            return 1
        return block.MAX_FILES_COUNT


class TeamsConfigSerializer(Serializer):
    enabled = BooleanField(source="is_team_assignment")
    teamsetName = SerializerMethodField()

    def get_teamsetName(self, block):
        if block.teamset_config is not None:
            return block.teamset_config.name
        return None


class SubmissionConfigSerializer(Serializer):
    startDatetime = SerializerMethodField()
    endDatetime = SerializerMethodField()
    _date_range = None

    textResponseConfig = TextResponseConfigSerializer(source="*")
    fileResponseConfig = FileResponseConfigSerializer(source="*")

    teamsConfig = TeamsConfigSerializer(source="*")

    def _get_start_end_date(self, xblock):
        """ Cached calculation of step due dates """
        if self._date_range is None:
            _, _, start, end = xblock.is_closed(step='submission')
            self._date_range = (
                start.isoformat() if start > DISTANT_PAST else None,
                end.isoformat() if end < DISTANT_FUTURE else None,
            )
        return self._date_range

    def get_startDatetime(self, xblock):
        return self._get_start_end_date(xblock)[0]

    def get_endDatetime(self, xblock):
        return self._get_start_end_date(xblock)[1]


class RubricFeedbackConfigSerializer(Serializer):
    description = CharField(source="rubric_feedback_prompt")  # is this this field?
    defaultText = CharField(source="rubric_feedback_default_text")


class RubricCriterionOptionSerializer(Serializer):
    name = CharField()
    label = CharField()
    points = IntegerField()
    description = CharField(source="explanation")


class RubricCriterionSerializer(Serializer):
    name = CharField(source="label")
    description = CharField(source="prompt")
    feedbackEnabled = SerializerMethodField()
    feedbackRequired = SerializerMethodField()
    options = RubricCriterionOptionSerializer(many=True)

    @staticmethod
    def _feedback(criterion):
        # Feedback is disabled as a default
        return criterion.get("feedback", "disabled")

    def get_feedbackEnabled(self, criterion):
        # Feedback can be specified as optional or required
        return self._feedback(criterion) != "disabled"

    def get_feedbackRequired(self, criterion):
        # Feedback can be specified as optional or required
        return self._feedback(criterion) == "required"


class RubricConfigSerializer(Serializer):
    showDuringResponse = BooleanField(source="show_rubric_during_response")
    feedbackConfig = RubricFeedbackConfigSerializer(source="*")
    criteria = RubricCriterionSerializer(
        many=True, source="rubric_criteria_with_labels"
    )


class AssessmentStepSettingsSerializer(Serializer):
    """
    Generic Assessments step, where we just need to know if the step is
    required given the ora.rubric_assessments source.
    """

    required = BooleanField(default=True)
    STEP_NAME = None  # Overridden by child classes

    def _get_step(self, rubric_assessments, step_name):
        """Get the assessment step config for a given step_name"""
        for step in rubric_assessments:
            if step["name"] == step_name:
                return step
        return None

    # pylint: disable=arguments-renamed
    def to_representation(self, xblock):
        assessment_step = self._get_step(xblock.rubric_assessments, self.STEP_NAME)
        # If we didn't find a step, it is not required
        if assessment_step is None:
            return {"required": False}

        assessment_step = dict(assessment_step)
        # Add overridden start and due dates for peer assessment and self assessment
        if self.STEP_NAME in ('peer-assessment', 'self-assessment'):
            _, _, start, due = xblock.is_closed(step=self.STEP_NAME)
            assessment_step['start'] = start.isoformat()
            assessment_step['due'] = due.isoformat()

        return super().to_representation(assessment_step)


class SelfSettingsSerializer(AssessmentStepSettingsSerializer):
    STEP_NAME = 'self-assessment'
    startDatetime = DateTimeField(source='start')
    endDatetime = DateTimeField(source='due')


class StudentTrainingSettingsSerializer(AssessmentStepSettingsSerializer):
    STEP_NAME = 'student-training'
    numberOfExamples = SerializerMethodField(source="*", default=0)

    def get_numberOfExamples(self, assessment):
        return len(assessment["examples"])


class PeerSettingsSerializer(AssessmentStepSettingsSerializer):
    STEP_NAME = 'peer-assessment'
    minNumberToGrade = IntegerField(source="must_grade")
    minNumberToBeGradedBy = IntegerField(source="must_be_graded_by")

    startDatetime = DateTimeField(source='start')
    endDatetime = DateTimeField(source='due')

    enableFlexibleGrading = BooleanField(
        source="enable_flexible_grading", required=False
    )

    gradingStrategy = CharField(
        source="grading_strategy",
        default=PeerGradingStrategy.MEDIAN,
    )


class StaffSettingsSerializer(AssessmentStepSettingsSerializer):
    STEP_NAME = 'staff-assessment'


class AssessmentStepsSettingsSerializer(Serializer):
    studentTraining = StudentTrainingSettingsSerializer(source="*")
    peer = PeerSettingsSerializer(source="*")
    # Workaround to allow reserved keyword in serializer key
    vars()["self"] = SelfSettingsSerializer(source='*')
    staff = StaffSettingsSerializer(source='*')


class AssessmentStepsSerializer(Serializer):
    order = SerializerMethodField()
    settings = AssessmentStepsSettingsSerializer(source="*")

    def get_order(self, block):
        return [
            STEP_NAME_MAPPINGS[WorkflowStep(step["name"]).workflow_step_name]
            for step in block.rubric_assessments
        ]


class LeaderboardConfigSerializer(Serializer):
    enabled = SerializerMethodField()
    numberOfEntries = IntegerField(source="leaderboard_show")

    def get_enabled(self, block):
        return block.leaderboard_show > 0


class OraBlockInfoSerializer(Serializer):
    """
    Main serializer for statically-defined ORA Block information
    """

    title = CharField()
    prompts = SerializerMethodField(source="*")
    baseAssetUrl = SerializerMethodField(source="*")

    submissionConfig = SubmissionConfigSerializer(source="*")
    assessmentSteps = AssessmentStepsSerializer(source="*")
    rubricConfig = RubricConfigSerializer(source="*")
    leaderboardConfig = LeaderboardConfigSerializer(source="*")

    def get_baseAssetUrl(self, block):
        # pylint: disable=protected-access
        return block.get_base_url_path_for_course_assets(block.course.id)

    def get_prompts(self, block):
        return [prompt["description"] for prompt in block.prompts]
