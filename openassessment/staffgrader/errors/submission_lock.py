"""
Errors around Submission Locking
"""


class SubmissionLockContestedError(Exception):
    """
    Error indicating trying to modify a lock that the user does not have access to modify.
    """
    error_code = 'ERR_LOCK_CONTESTED'

    @property
    def error_code(self):
        return self.error_code
