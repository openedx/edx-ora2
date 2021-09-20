"""
Errors around Submission Locking
"""

class SubmissionLockContestedError(Exception):
    """
    Error indicating trying to modify a lock that the user does not have access to modify.
    """
