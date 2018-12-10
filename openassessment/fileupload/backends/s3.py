import logging

import boto3

from django.conf import settings

from ..exceptions import FileUploadInternalError
from .base import BaseBackend

logger = logging.getLogger("openassessment.fileupload.api")


class Backend(BaseBackend):

    def get_upload_url(self, key, content_type):
        bucket_name, key_name = self._retrieve_parameters(key)
        try:
            client = _connect_to_s3()
            return client.generate_presigned_url(
                ExpiresIn=self.UPLOAD_URL_TIMEOUT,
                ClientMethod='put_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': key_name
                },
                HttpMethod="PUT"
            )
        except Exception as ex:
            logger.exception(
                u"An internal exception occurred while generating an upload URL."
            )
            raise FileUploadInternalError(ex)

    def get_download_url(self, key):
        bucket_name, key_name = self._retrieve_parameters(key)
        try:
            client = _connect_to_s3()
            return client.generate_presigned_url(
                ExpiresIn=self.DOWNLOAD_URL_TIMEOUT,
                ClientMethod='get_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': key_name
                },
                HttpMethod="GET"
            )
        except Exception as ex:
            logger.exception(
                u"An internal exception occurred while generating a download URL."
            )
            raise FileUploadInternalError(ex)

    def remove_file(self, key):
        bucket_name, key_name = self._retrieve_parameters(key)
        client = _connect_to_s3()
        resp = client.delete_objects(
            Bucket=bucket_name,
            Delete={
                'Objects': [{'Key':key_name}]
            }
        )
        if 'Deleted' in resp and any(key_name == deleted_dict['Key'] for deleted_dict in resp['Deleted']):
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

    return boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )
