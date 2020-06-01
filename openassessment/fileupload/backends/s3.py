""" S3 bucket file upload backend. """


import logging

from django.conf import settings

import boto

from ..exceptions import FileUploadInternalError
from .base import BaseBackend

logger = logging.getLogger("openassessment.fileupload.api")  # pylint: disable=invalid-name


class Backend(BaseBackend):
    """ S3 Bucked File Upload Backend. """

    def get_upload_url(self, key, content_type):
        bucket_name, key_name = self._retrieve_parameters(key)
        try:
            conn = _connect_to_s3()
            upload_url = conn.generate_url(
                expires_in=self.UPLOAD_URL_TIMEOUT,
                method='PUT',
                bucket=bucket_name,
                key=key_name,
                headers={'Content-Length': '5242880', 'Content-Type': content_type}
            )
            return upload_url
        except Exception as ex:
            logger.exception(
                u"An internal exception occurred while generating an upload URL."
            )
            raise FileUploadInternalError(ex)

    def get_download_url(self, key):
        bucket_name, key_name = self._retrieve_parameters(key)
        try:
            conn = _connect_to_s3()
            bucket = conn.get_bucket(bucket_name)
            s3_key = bucket.get_key(key_name)
            return s3_key.generate_url(expires_in=self.DOWNLOAD_URL_TIMEOUT) if s3_key else ""
        except Exception as ex:
            logger.exception(
                u"An internal exception occurred while generating a download URL."
            )
            raise FileUploadInternalError(ex)

    def remove_file(self, key):
        bucket_name, key_name = self._retrieve_parameters(key)
        conn = _connect_to_s3()
        bucket = conn.get_bucket(bucket_name)
        s3_key = bucket.get_key(key_name)
        if s3_key:
            bucket.delete_key(s3_key)
            return True
        return False


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
