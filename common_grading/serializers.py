from rest_framework import serializers
from models import Essay


class EssaySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Essay
        fields = ('student_id', 'problem_id', 'essay_body', 'grades', 'status', 'grading_type')