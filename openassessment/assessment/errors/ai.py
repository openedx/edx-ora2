"""
Errors related to AI assessment.
"""

from celery.exceptions import InvalidTaskError, NotConfigured, NotRegistered, QueueNotFound
from socket import error as socket_error

ANTICIPATED_CELERY_ERRORS = (InvalidTaskError, NotConfigured, NotRegistered, QueueNotFound, socket_error)

class AIError(Exception):
    """
    A general error occurred while using the AI assessment API.
    """
    pass


class AITrainingRequestError(AIError):
    """
    There was a problem with the request sent to the AI assessment API.
    """
    pass


class AITrainingInternalError(AIError):
    """
    An unexpected error occurred while using the AI assessment API.
    """
    pass


class AIGradingRequestError(AIError):
    """
    There was a problem with the request sent to the AI assessment API.
    """
    pass


class AIGradingInternalError(AIError):
    """
    An unexpected error occurred while using the AI assessment API.
    """
    pass


class AIReschedulingRequestError(AIError):
    """
    There was a problem with the request sent to the AI assessment API.
    """
    pass


class AIReschedulingInternalError(AIError):
    """
    An unexpected error occurred while using the AI assessment API.
    """
    pass
