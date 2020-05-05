""" File Uploads backends. """
from __future__ import absolute_import

import abc
import mimetypes

import six

from django.conf import settings

from ..exceptions import FileUploadInternalError, FileUploadRequestError


class Settings:
    """Store settings related to file upload

    The following settings are used:

        FILE_UPLOAD_STORAGE_BUCKET_NAME (str, required): name of the bucket
        (AWS or local file directory) to which content will be uploaded.

        FILE_STORAGE_STORAGE_PREFIX (str, defaults to
        DEFAULT_FILE_UPLOAD_STORAGE_PREFIX): this will be used to prefix all
        stored file names. The specified file prefix for the storage must be
        publicly viewable or all uploaded files will not be seen.
    """
    DEFAULT_FILE_UPLOAD_STORAGE_PREFIX = "submissions_attachments"  # pylint: disable=invalid-name
    FILE_EXTENSIONS_BY_TYPE = {
        'image/gif': '.gif',
        'image/jpeg': '.jpg',
        'image/pjpeg': '.jpg',
        'image/png': '.png',
        'application/pdf': '.pdf',
        'application/msword': '.doc',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
    }

    @classmethod
    def get_bucket_name(cls):
        bucket_name = getattr(settings, "FILE_UPLOAD_STORAGE_BUCKET_NAME", None)
        if not bucket_name:
            raise FileUploadInternalError("No bucket name configured for FileUpload Service.")
        return bucket_name

    @classmethod
    def get_prefix(cls):
        """Return the prefix for stored files.

        Defaults to the DEFAULT_FILE_UPLOAD_STORAGE_PREFIX class attribute.
        """
        return getattr(settings, "FILE_UPLOAD_STORAGE_PREFIX", cls.DEFAULT_FILE_UPLOAD_STORAGE_PREFIX)

    @classmethod
    def guess_extension(cls, mime_type):
        """
        Guess a file extension (with a leading dot) given its mime type. If no
        file is found, return an empty extension.
        """
        if mime_type in cls.FILE_EXTENSIONS_BY_TYPE:
            return cls.FILE_EXTENSIONS_BY_TYPE[mime_type]
        return mimetypes.guess_extension(mime_type) or ''


class BaseBackend(six.with_metaclass(abc.ABCMeta, object)):
    """ Base class for file upload backends. """

    UPLOAD_URL_TIMEOUT = 3600

    # Time (in seconds) before a download url expires
    DOWNLOAD_URL_TIMEOUT = 1000

    @abc.abstractmethod
    def get_upload_url(self, key, content_type):
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
        raise NotImplementedError

    @abc.abstractmethod
    def get_download_url(self, key):
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
        raise NotImplementedError

    @abc.abstractmethod
    def remove_file(self, key):
        """
        Remove file from the storage

        Args:
            key (str): A unique identifier used to identify the data requested for remove.

        Returns:
            True if file was successfully removed or False is file was not removed or was not was not found.
        """
        raise NotImplementedError

    def _retrieve_parameters(self, key):
        """
        Simple utility function to validate settings and arguments before compiling
        bucket names and key names.

        Args:
            key (str): Custom key passed in with the request.

        Returns:
            A tuple of the bucket name and the complete key.

        Raises:
            FileUploadRequestError
            FileUploadInternalError

        """
        if not key:
            raise FileUploadRequestError("Key required for URL request")
        return Settings.get_bucket_name(), self._get_key_name(key)

    def _get_key_name(self, key):
        """Construct a key name with the given string and configured prefix.

        Constructs a unique key with the specified path and the service-specific
        configured prefix.

        Args:
            key (str): Key to identify data for both upload and download.

        Returns:
            A key name (str) to use constructing URLs.
        """
        return u"{prefix}/{key}".format(
            prefix=Settings.get_prefix(),
            key=key
        )
