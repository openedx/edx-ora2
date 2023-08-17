"""
Errors and exceptions for submission API
"""


class NoTeamToCreateSubmissionForError(Exception):
    pass


class EmptySubmissionError(Exception):
    pass


class DraftSaveException(Exception):
    pass


class SubmissionValidationException(Exception):
    pass


class AnswerTooLongException(Exception):
    pass


class SubmitInternalError(Exception):
    pass


class StudioPreviewException(Exception):
    pass


class MultipleSubmissionsException(Exception):
    pass
