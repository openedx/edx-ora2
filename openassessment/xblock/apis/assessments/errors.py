"""
Assessment API Errors
"""


class ReviewerMustHaveSubmittedException(Exception):
    pass


class ServerClientUUIDMismatchException(Exception):
    pass


class StepConfigurationNotFound(Exception):
    pass
