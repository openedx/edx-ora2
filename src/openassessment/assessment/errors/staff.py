"""
Errors for the staff assessment api.
"""

from .base import AssessmentError


class StaffAssessmentError(AssessmentError):
    """Generic Staff Assessment Error

    Raised when an error occurs while processing a request related to
    staff assessment.

    """


class StaffAssessmentRequestError(StaffAssessmentError):
    """Error indicating insufficient or incorrect parameters in the request.

    Raised when the request does not contain enough information, or incorrect
    information which does not allow the request to be processed.

    """


class StaffAssessmentInternalError(StaffAssessmentError):
    """Error indicating an internal problem independent of API use.

    Raised when an internal error has occurred. This should be independent of
    the actions or parameters given to the API.

    """
