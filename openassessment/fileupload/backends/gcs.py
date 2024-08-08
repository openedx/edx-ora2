"""GCS Bucket File Upload Backend."""
import functools
import logging

from ..exceptions import FileUploadInternalError
from .base import BaseBackend

log = logging.getLogger("openassessment.fileupload.api")  # pylint: disable=invalid-name


def catch_broad_exception(method):
    """Decorator to catch broad exceptions, log them, and raise a FileUploadInternalError."""
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except Exception as ex:  # pylint: disable=broad-except
            log.exception(
                f"Internal exception occurred while executing ora2 file-upload backend gcs.{method.__name__}: {str(ex)}"
            )
            raise FileUploadInternalError(ex) from ex
    return wrapper


class Backend(BaseBackend):
    """ GCS Bucket File Upload Backend. """

    @catch_broad_exception
    def get_upload_url(self, key, content_type):
        """Get a signed URL for uploading a file to GCS"""
        bucket_name, key_name = self._retrieve_parameters(key)
        blob = get_blob_object(bucket_name, key_name)

        return blob.generate_signed_url(
            version="v4",
            expiration=self.UPLOAD_URL_TIMEOUT,
            method="PUT",
            content_type=content_type,
        )

    @catch_broad_exception
    def get_download_url(self, key):
        """Get a signed URL for downloading a file from GCS"""
        bucket_name, key_name = self._retrieve_parameters(key)
        blob = get_blob_object(bucket_name, key_name)
        if not blob.exists():
            return ""

        return blob.generate_signed_url(
            version="v4",
            expiration=self.DOWNLOAD_URL_TIMEOUT,
            method="GET",
        )

    @catch_broad_exception
    def remove_file(self, key):
        """Remove a file from GCS"""
        bucket_name, key_name = self._retrieve_parameters(key)
        blob = get_blob_object(bucket_name, key_name)
        if blob.exists():
            blob.delete()
            return True

        return False


def get_blob_object(bucket_name, key_name):
    """Get a blob object from GCS"""
    # By default; avoid the need of google-cloud-storage library. It will be only needed if gcs backend is used.
    from google.cloud import storage  # pylint: disable=import-outside-toplevel

    client = storage.Client()
    return client.bucket(bucket_name).blob(key_name)
