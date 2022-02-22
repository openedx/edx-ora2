"""
Serializers for the Submission List endpoint
"""
from rest_framework import serializers
from openassessment.assessment.models.staff import StaffWorkflow


class MissingContextException(Exception):
    pass


# pylint: disable=abstract-method
class SubmissionListScoreSerializer(serializers.Serializer):
    pointsEarned = serializers.IntegerField(source='points_earned')
    pointsPossible = serializers.IntegerField(source='points_possible')


class SubmissionListSerializer(serializers.ModelSerializer):
    """
    Serialized info about an item returned from the submission list endpoint
    """
    class Meta:
        model = StaffWorkflow
        fields = [
            'submissionUuid',
            'dateSubmitted',
            'dateGraded',
            'gradingStatus',
            'lockStatus',
            'gradedBy',
            'username',
            'teamName',
            'score'
        ]
        read_only_fields = fields

    requires_context = True

    # Always required context
    CONTEXT_IS_TEAM_ASSIGNMENT = 'is_team_assignment'
    CONTEXT_ANON_ID_TO_USERNAME = 'anonymous_id_to_username'
    CONTEXT_SUB_TO_ASSESSMENT = 'submission_uuid_to_assessment'

    # Individual submission context
    CONTEXT_SUB_TO_ANON_ID = 'submission_uuid_to_student_id'

    # Team submission context
    CONTEXT_SUB_TO_TEAM_ID = 'team_submission_uuid_to_team_id'
    CONTEXT_TEAM_ID_TO_TEAM_NAME = 'team_id_to_team_name'

    def _is_team_submission(self):
        """Utility function for if this is team vs individual submisison list"""
        return self.context.get(self.CONTEXT_IS_TEAM_ASSIGNMENT, False)

    def _verify_required_context(self, context):
        """Verify that required individual or team context is present for serialization"""
        context_keys = set(context.keys())

        # Required context for all submission types
        required_context = set([
            self.CONTEXT_IS_TEAM_ASSIGNMENT,
            self.CONTEXT_ANON_ID_TO_USERNAME,
            self.CONTEXT_SUB_TO_ASSESSMENT
        ])

        # Required team context
        if context.get(self.CONTEXT_IS_TEAM_ASSIGNMENT, False):
            required_context.update([
                self.CONTEXT_SUB_TO_TEAM_ID,
                self.CONTEXT_TEAM_ID_TO_TEAM_NAME,
            ])
        # Required individual context
        else:
            required_context.update([
                self.CONTEXT_SUB_TO_ANON_ID
            ])

        missing_context = required_context - context_keys
        if missing_context:
            raise ValueError(f"Missing required context {' ,'.join(missing_context)}")

    def __init__(self, *args, **kwargs):
        self._verify_required_context(kwargs.get('context', {}))
        super().__init__(*args, **kwargs)

    submissionUuid = serializers.CharField(source='submission_uuid')
    dateSubmitted = serializers.CharField(source='created_at')
    dateGraded = serializers.CharField(source='grading_completed_at')
    dateGraded = serializers.SerializerMethodField()
    gradingStatus = serializers.CharField(source='grading_status')
    lockStatus = serializers.CharField(source='lock_status')
    gradedBy = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    teamName = serializers.SerializerMethodField()
    score = serializers.SerializerMethodField()

    def _get_username_from_context(self, anonymous_user_id):
        try:
            return self.context[self.CONTEXT_ANON_ID_TO_USERNAME][anonymous_user_id]
        except KeyError as e:
            raise MissingContextException(f"Username not found for anonymous user id {anonymous_user_id}") from e

    def _get_team_name_from_context(self, team_id):
        try:
            return self.context[self.CONTEXT_TEAM_ID_TO_TEAM_NAME][team_id]
        except KeyError as e:
            raise MissingContextException(f"Team name not found for team id {team_id}") from e

    def _get_team_id_from_context(self, team_submission_uuid):
        try:
            return self.context[self.CONTEXT_SUB_TO_TEAM_ID][team_submission_uuid]
        except KeyError as e:
            raise MissingContextException(
                f"No submitter anonymous user id found for team submission uuid {team_submission_uuid}"
            ) from e

    def _get_anonymous_id_from_context(self, submission_uuid):
        try:
            return self.context[self.CONTEXT_SUB_TO_ANON_ID][submission_uuid]
        except KeyError as e:
            raise MissingContextException(
                f"No submitter anonymous user id found for submission uuid {submission_uuid}"
            ) from e

    def get_dateGraded(self, workflow):
        return str(workflow.grading_completed_at)

    def get_gradedBy(self, workflow):
        if workflow.scorer_id:
            return self._get_username_from_context(workflow.scorer_id)
        else:
            return None

    def get_username(self, workflow):
        if self._is_team_submission():
            return None
        return self._get_username_from_context(
            self._get_anonymous_id_from_context(workflow.identifying_uuid)
        )

    def get_teamName(self, workflow):
        if not self._is_team_submission():
            return None
        return self._get_team_name_from_context(
            self._get_team_id_from_context(workflow.identifying_uuid)
        )

    def get_score(self, workflow):
        assessment = self.context[self.CONTEXT_SUB_TO_ASSESSMENT].get(workflow.identifying_uuid)
        if assessment:
            return SubmissionListScoreSerializer(assessment).data
        else:
            return {}
