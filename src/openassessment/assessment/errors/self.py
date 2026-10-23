"""
Errors for self-assessment
"""
from .base import AssessmentError


class SelfAssessmentError(AssessmentError):
    """Generic Self Assessment Error

    Raised when an error occurs while processing a request related to the
    Self Assessment Workflow.

    """


class SelfAssessmentRequestError(SelfAssessmentError):
    """
    There was a problem with the request for a self-assessment.
    """


class SelfAssessmentInternalError(SelfAssessmentError):
    """
    There was an internal problem while accessing the self-assessment api.
    """
