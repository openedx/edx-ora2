"""
Errors around Submission Locking
"""


class SubmissionLockContestedError(Exception):
    """
    Error indicating trying to modify a lock that the user does not have access to modify.
    """
    error_code = 'ERR_LOCK_CONTESTED'

    def get_error_code(self):
        return self.error_code
