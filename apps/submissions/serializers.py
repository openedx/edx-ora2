"""
Serializers are created to ensure models do not have to be accessed outside the
scope of the Tim APIs.
"""
import json
from rest_framework import serializers
from submissions.models import StudentItem, Submission, Score


class JsonFieldError(Exception):
    """
    An error occurred while serializing/deserializing JSON.
    """
    pass


class JsonField(serializers.WritableField):
    """
    JSON-serializable field.
    """
    def to_native(self, obj):
        """
        Deserialize the JSON string.

        Args:
            obj (str): The JSON string stored in the database.

        Returns:
            JSON-serializable

        Raises:
            JsonFieldError: The field could not be deserialized.
        """
        try:
            return json.loads(obj)
        except (TypeError, ValueError):
            raise JsonFieldError(u"Could not deserialize as JSON: {}".format(obj))

    def from_native(self, data):
        """
        Serialize an object to JSON.

        Args:
            data (JSON-serializable): The data to serialize.

        Returns:
            str

        Raises:
            ValueError: The data could not be serialized as JSON.
        """
        try:
            return json.dumps(data)
        except (TypeError, ValueError):
            raise JsonFieldError(u"Could not serialize as JSON: {}".format(data))


class StudentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentItem
        fields = ('student_id', 'course_id', 'item_id', 'item_type')


class SubmissionSerializer(serializers.ModelSerializer):

    answer = JsonField(source='raw_answer')

    def validate_answer(self, attrs, source):
        """Check that the answer is within an acceptable size range."""
        value = attrs[source]
        if len(value) > Submission.MAXSIZE:
            raise serializers.ValidationError("Maximum answer size exceeded.")
        return attrs

    class Meta:
        model = Submission
        fields = (
            'uuid',
            'student_item',
            'attempt_number',
            'submitted_at',
            'created_at',

            # Computed
            'answer',
        )


class ScoreSerializer(serializers.ModelSerializer):

    submission_uuid = serializers.Field(source='submission_uuid')

    class Meta:
        model = Score
        fields = (
            'student_item',
            'submission',
            'points_earned',
            'points_possible',
            'created_at',

            # Computed
            'submission_uuid',
        )

