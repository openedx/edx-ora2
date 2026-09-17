"""
Assessment API Errors
"""

from openassessment.assessment.errors import AssessmentError


class InvalidStateToAssess(AssessmentError):
    pass


class ReviewerMustHaveSubmittedException(InvalidStateToAssess):
    pass


class ServerClientUUIDMismatchException(AssessmentError):
    pass
