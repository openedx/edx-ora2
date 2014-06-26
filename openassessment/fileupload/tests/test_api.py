import boto
from boto.s3.key import Key
import ddt
from django.test import TestCase
from django.test.utils import override_settings
from moto import mock_s3
from openassessment.fileupload import api

@ddt.ddt
class TestFileUploadService(TestCase):

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        AWS_STORAGE_BUCKET_NAME="mybucket"
    )
    def test_get_upload_url(self):
        conn = boto.connect_s3()
        conn.create_bucket('mybucket')
        uploadUrl = api.get_upload_url("foo", "bar")
        self.assertIn("https://mybucket.s3.amazonaws.com/submissions_attachments/foo", uploadUrl)

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        AWS_STORAGE_BUCKET_NAME="mybucket"
    )
    def test_get_download_url(self):
        conn = boto.connect_s3()
        bucket = conn.create_bucket('mybucket')
        key = Key(bucket)
        key.key = "submissions_attachments/foo"
        key.set_contents_from_string("How d'ya do?")
        downloadUrl = api.get_download_url("foo")
        self.assertIn("https://mybucket.s3.amazonaws.com/submissions_attachments/foo", downloadUrl)

