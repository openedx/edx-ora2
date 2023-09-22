"""
Submission-related serializers for ORA's BFF.

These are the response shapes that power the MFE implementation of the ORA UI.
"""
# pylint: disable=abstract-method

from rest_framework.serializers import (
    Serializer,
)


class SubmissionSerializer(Serializer):
    """
    submission: (Object, can be empty)
    {
        // Status info
        hasSubmitted: (Bool)
        hasCancelled: (Bool)
        hasReceivedGrade: (Bool)

        // Team info needed for team responses
        // Empty object for individual submissions
        teamInfo: (Object)

        // The actual response to view
        response: (Object)
    }
    """
