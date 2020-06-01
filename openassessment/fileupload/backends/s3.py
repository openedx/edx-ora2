""" S3 bucket file upload backend. """


import logging

from django.conf import settings

import botocore
import boto3

from ..exceptions import FileUploadInternalError
from .base import BaseBackend

log = logging.getLogger(
    "openassessment.fileupload.api"
)  # pylint: disable=invalid-name


class Backend(BaseBackend):
    """ S3 Bucked File Upload Backend. """

    def get_upload_url(self, key, content_type):
        bucket_name, key_name = self._retrieve_parameters(key)
        try:
            conn = _connect_to_s3()
            return conn.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket_name,
                    "Key": key_name,
                    "ContentType": content_type,
                },
                ExpiresIn=self.UPLOAD_URL_TIMEOUT,
            )
        except Exception as ex:
            log.exception(
                u"An internal exception occurred while generating an upload URL."
            )
            raise FileUploadInternalError(ex)

    def get_download_url(self, key):
        bucket_name, key_name = self._retrieve_parameters(key)
        try:
            conn = _connect_to_s3()
            if not object_exists(conn, bucket_name, key_name):
                return ""
            return conn.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": key_name},
                ExpiresIn=self.DOWNLOAD_URL_TIMEOUT,
            )
        except Exception as ex:
            log.exception(
                u"An internal exception occurred while generating a download URL."
            )
            raise FileUploadInternalError(ex)

    def remove_file(self, key):
        bucket_name, key_name = self._retrieve_parameters(key)
        conn = _connect_to_s3()
        if object_exists(conn, bucket_name, key_name):
            conn.delete_object(Bucket=bucket_name, Key=key_name)
            return True
        return False


def _connect_to_s3():
    """Connect to s3

    Creates a connection to s3 for file URLs.
    """
    # Try to get the AWS credentials from settings if they are available
    # If not, these will default to `None`, and boto3 will try to use
    # environment vars or configuration files instead.
    aws_access_key_id = getattr(settings, "AWS_ACCESS_KEY_ID", None)
    aws_secret_access_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
    endpoint_url = getattr(settings, "AWS_S3_ENDPOINT_URL", None)

    return boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=endpoint_url,
    )


def object_exists(conn, bucket_name, key_name):
    """
    Check if a key exists in the given S3 bucket.
    """
    try:
        conn.head_object(Bucket=bucket_name, Key=key_name)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        raise e
    return True
