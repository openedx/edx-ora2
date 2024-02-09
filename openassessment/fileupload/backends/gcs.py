"""GCS Bucket File Upload Backend."""

from google.cloud import storage
import logging

from ..exceptions import FileUploadInternalError
from .base import BaseBackend

log = logging.getLogger("openassessment.fileupload.api")  # pylint: disable=invalid-name


class GCSBackend(BaseBackend):
    """ GCS Bucket File Upload Backend. """

    def get_upload_url(self, key, content_type):
        """Get a signed URL for uploading a file to GCS"""
        bucket_name, key_name = self._retrieve_parameters(key)
        try:
            client = _connect_to_gcs()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(key_name)
            url = blob.generate_signed_url(
                version="v4",
                expiration=self.UPLOAD_URL_TIMEOUT,
                method="PUT",
                content_type=content_type,
            )
            return url
        except Exception as ex:
            log.exception("An internal exception occurred while generating an upload URL.")
            raise FileUploadInternalError(ex) from ex

    def get_download_url(self, key):
        """Get a signed URL for downloading a file from GCS"""
        bucket_name, key_name = self._retrieve_parameters(key)
        try:
            client = _connect_to_gcs()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(key_name)
            if not blob.exists():
                return ""
            url = blob.generate_signed_url(
                version="v4",
                expiration=self.DOWNLOAD_URL_TIMEOUT,
                method="GET",
            )
            return url
        except Exception as ex:
            log.exception("An internal exception occurred while generating a download URL.")
            raise FileUploadInternalError(ex) from ex

    def remove_file(self, key):
        """Remove a file from GCS"""
        bucket_name, key_name = self._retrieve_parameters(key)
        client = _connect_to_gcs()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(key_name)
        if blob.exists():
            blob.delete()
            return True
        return False


def _connect_to_gcs():
    """Connect to Google Cloud Storage"""
    return storage.Client()


def object_exists(client, bucket_name, key_name):
    """Check if a key exists in the given GCS bucket"""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(key_name)
    return blob.exists()
