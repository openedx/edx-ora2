"""
Errors related to AI assessment.
"""


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
