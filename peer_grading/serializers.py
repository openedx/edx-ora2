from rest_framework import serializers
from models import Status


class StatusSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Status
        fields = ('student_id', 'problem_id', 'grading_status')