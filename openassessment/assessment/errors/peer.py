"""
Errors for the peer assessment.
"""
from .base import AssessmentError


class PeerAssessmentError(AssessmentError):
    """Generic Peer Assessment Error

    Raised when an error occurs while processing a request related to the
    Peer Assessment Workflow.

    """


class PeerAssessmentRequestError(PeerAssessmentError):
    """Error indicating insufficient or incorrect parameters in the request.

    Raised when the request does not contain enough information, or incorrect
    information which does not allow the request to be processed.

    """


class PeerAssessmentWorkflowError(PeerAssessmentError):
    """Error indicating a step in the workflow cannot be completed,

    Raised when the action taken cannot be completed in the workflow. This can
    occur based on parameters specific to the Submission, User, or Peer Scorers.

    """


class PeerAssessmentInternalError(PeerAssessmentError):
    """Error indicating an internal problem independent of API use.

    Raised when an internal error has occurred. This should be independent of
    the actions or parameters given to the API.

    """
