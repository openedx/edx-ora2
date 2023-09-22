"""
Serializer for assessments
"""
# pylint: disable=abstract-method

from rest_framework.serializers import Serializer


class AssessmentResponseSerializer(Serializer):
    """
    Given we want to load an assessment response,
    gather the appropriate response and serialize.

    Data same shape as Submission, but coming from different sources.
    """
