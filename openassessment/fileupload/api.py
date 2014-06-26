"""
The File Upload application is designed to allow the management of files
associated with submissions. This can be used to upload new files and provide
URLs to the new location.

"""
import boto
from boto.s3.key import Key
from django.conf import settings


class FileUploadError(Exception):
    """An error related to uploading files

    This is the generic error raised when a file could not be uploaded.

    """
    pass


class FileUploadInternalError(FileUploadError):
    """An error internal to the File Upload API.

    This is an error raised when file upload failed due to internal problems in
    the File Upload API, beyond the intervention of the requester.

    """
    pass


class FileUploadRequestError(FileUploadError):
    """This error is raised when the request has invalid parameters for upload.

    This error will be raised if the file being uploaded is somehow invalid,
    based on type restrictions, size restrictions, upload limits, etc.

    """
    pass

FILE_STORAGE = "submissions_attachments"


def get_upload_url(key, content_type):
    """Request a one-time upload URL to upload files.

    Requests a URL for a one-time file upload.

    Args:
        key (str): A unique identifier used to construct the upload location and
            later, can be used to retrieve the same information. This service
            must be able to identify data for both upload and download using
            this key.
        content_type (str): The content type for the file.

    Returns:
        A URL (str) to use for a one-time upload.

    Raises:
        FileUploadInternalError: Raised when an internal error occurs while
            retrieving a one-time URL.
        FileUploadRequestError: Raised when the request failed due to
            request restrictions

    """
    try:
        conn = _connect_to_s3()
        bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
        key_name = _get_key_name(key)
        upload_url = conn.generate_url(
            3600,
            'PUT',
            bucket_name,
            key_name,
            headers={'Content-Length': '5242880', 'Content-Type': content_type}
        )
        return upload_url
    except Exception as ex:
        raise FileUploadInternalError(ex)


def get_download_url(key):
    """Requests a URL to download the related file from.

    Requests a URL for the given student_item.

    Args:
        key (str): A unique identifier used to identify the data requested for
            download. This service must be able to identify data for both
            upload and download using this key.

    Returns:
        A URL (str) to use for downloading related files. If no file is found,
        returns an empty string.

    """
    conn = _connect_to_s3()
    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)

    if not bucket_name or not key:
        return ""

    bucket = conn.get_bucket(bucket_name)
    key_name = _get_key_name(key)
    s3_key = bucket.get_key(key_name)
    return s3_key.generate_url(expires_in=1000) if s3_key else ""


def _connect_to_s3():
    """Connect to s3

    Creates a connection to s3 for file URLs.

    """
    # Try to get the AWS credentials from settings if they are available
    # If not, these will default to `None`, and boto will try to use
    # environment vars or configuration files instead.
    aws_access_key_id = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
    aws_secret_access_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
    return boto.connect_s3(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )


def _get_key_name(key):
    """Construct a key name related to the student item.

    Constructs a unique key that is specific to the student item.

    Args:
        key (str): Key to identify data for both upload and download.

    Returns:
        A key name (str) to use constructing URLs.
    """
    # The specified file prefix for the storage must be publicly viewable
    # or all uploaded images will not be seen.
    prefix = getattr(settings, "ORA2_FILE_STORAGE_PREFIX", FILE_STORAGE)
    return u"{prefix}/{key}".format(
        prefix=prefix,
        key=key
    )