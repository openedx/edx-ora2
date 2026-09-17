""" Exceptions for FileUploads. """


class FileUploadError(Exception):
    """An error related to uploading files

    This is the generic error raised when a file could not be uploaded.

    """


class FileUploadInternalError(FileUploadError):
    """An error internal to the File Upload API.

    This is an error raised when file upload failed due to internal problems in
    the File Upload API, beyond the intervention of the requester.

    """


class FileUploadRequestError(FileUploadError):
    """This error is raised when the request has invalid parameters for upload.

    This error will be raised if the file being uploaded is somehow invalid,
    based on type restrictions, size restrictions, upload limits, etc.

    """
