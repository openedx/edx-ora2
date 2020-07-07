"""
ORA Assessment Data Serializers.
"""
from rest_framework import serializers


class OraResponsesSerializer(serializers.Serializer):
    """
    Serializer for the ORA Assessment Data shown in instructor dashboard.
    """
    peer_assessment = serializers.IntegerField(source='peer')
    waiting = serializers.IntegerField()
    training = serializers.IntegerField()
    self_assessment = serializers.IntegerField(source='self')
    staff_assessment = serializers.IntegerField(source='staff')
    cancelled = serializers.IntegerField()
    done = serializers.IntegerField()
    teams = serializers.IntegerField()
    total = serializers.IntegerField()


class OraAssesmentDataSerializer(serializers.Serializer):
    """
    Serializer for the ORA Assessment Data shown in instructor dashboard.
    """
    id = serializers.CharField()
    name = serializers.CharField()
    parent_id = serializers.CharField()
    parent_name = serializers.CharField()
    staff_assessment = serializers.BooleanField()
    responses = OraResponsesSerializer()