"""
Errors and exceptions for submission API
"""


class NoTeamToCreateSubmissionForError(Exception):
    pass


class EmptySubmissionError(Exception):
    pass


class MissingFilesError(Exception):
    """Raised when a response declares files that are not present in storage."""

    def __init__(self, file_names):
        self.file_names = file_names
        super().__init__(
            "Response declares files that are not present in storage: {}".format(
                ", ".join(file_names)
            )
        )


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


class DeleteNotAllowed(Exception):
    pass


class OnlyOneFileAllowedException(Exception):
    pass


class UnsupportedFileTypeException(Exception):
    pass
