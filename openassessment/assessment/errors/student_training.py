"""
Errors for training assessment type.
"""


class StudentTrainingError(Exception):
    """
    Error occurred in a training API call.
    """


class StudentTrainingRequestError(StudentTrainingError):
    """
    There was a problem with a request made to the training API.
    """


class StudentTrainingInternalError(StudentTrainingError):
    """
    An internal error occurred while processing a request to the training API.
    """
