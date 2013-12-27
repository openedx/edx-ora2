from rest_framework import serializers
from models import PeerGradingStatus, PeerGradedEssay


class PeerGradedEssaySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PeerGradedEssay
        fields = ('student_id', 'problem_id', 'essay_body', 'grades', 'status')


class PeerGradingStatusSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = PeerGradingStatus
        fields = ('student_id', 'problem_id', 'grading_status')