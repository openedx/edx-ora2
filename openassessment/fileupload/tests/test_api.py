# -*- coding: utf-8 -*-

import boto
from boto.s3.key import Key
import ddt

import json
import os
import shutil
import tempfile

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse

from moto import mock_s3
from mock import patch
from nose.tools import raises

from openassessment.fileupload import api
from openassessment.fileupload import exceptions
from openassessment.fileupload import views_filesystem as views
from openassessment.fileupload.backends.base import Settings as FileUploadSettings
from openassessment.fileupload.backends.filesystem import get_cache as get_filesystem_cache

@ddt.ddt
class TestFileUploadService(TestCase):

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
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
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
    )
    def test_get_download_url(self):
        conn = boto.connect_s3()
        bucket = conn.create_bucket('mybucket')
        key = Key(bucket)
        key.key = "submissions_attachments/foo"
        key.set_contents_from_string("How d'ya do?")
        downloadUrl = api.get_download_url("foo")
        self.assertIn("https://mybucket.s3.amazonaws.com/submissions_attachments/foo", downloadUrl)

    @raises(exceptions.FileUploadInternalError)
    def test_get_upload_url_no_bucket(self):
        api.get_upload_url("foo", "bar")

    @raises(exceptions.FileUploadRequestError)
    def test_get_upload_url_no_key(self):
        api.get_upload_url("", "bar")

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
    )
    @patch.object(boto, 'connect_s3')
    @raises(exceptions.FileUploadInternalError)
    def test_get_upload_url_error(self, mock_s3):
        mock_s3.side_effect = Exception("Oh noes")
        api.get_upload_url("foo", "bar")

    @mock_s3
    @override_settings(
        AWS_ACCESS_KEY_ID='foobar',
        AWS_SECRET_ACCESS_KEY='bizbaz',
        FILE_UPLOAD_STORAGE_BUCKET_NAME="mybucket"
    )
    @patch.object(boto, 'connect_s3')
    @raises(exceptions.FileUploadInternalError, mock_s3)
    def test_get_download_url_error(self, mock_s3):
        mock_s3.side_effect = Exception("Oh noes")
        api.get_download_url("foo")


@override_settings(
    ORA2_FILEUPLOAD_BACKEND="filesystem",
    ORA2_FILEUPLOAD_ROOT='/tmp',
    ORA2_FILEUPLOAD_CACHE_NAME='default',
    FILE_UPLOAD_STORAGE_BUCKET_NAME="testbucket",
)
class TestFileUploadServiceWithFilesystemBackend(TestCase):
    """
    Test open assessment file upload to local file storage.
    """

    def setUp(self):
        self.backend = api.backends.get_backend()

        self.content = tempfile.TemporaryFile()
        self.content.write("foobar content")
        self.content.seek(0)

        self.key = None
        self.key_name = None
        self.set_key("myfile.jpg")
        self.content_type = "image/jpeg"

        get_filesystem_cache().clear()
        self.delete_data(self.key_name)


    def tearDown(self):
        self.delete_data(self.key_name)

    def set_key(self, key):
        self.key = key
        self.key_name = os.path.join(FileUploadSettings.get_prefix(), self.key)

    def delete_data(self, key_name):
        try:
            path = views.get_data_path(key_name)
            if os.path.exists(path):
                shutil.rmtree(path)
        except exceptions.FileUploadInternalError:
            pass

    def test_get_backend(self):
        self.assertTrue(isinstance(self.backend, api.backends.filesystem.Backend))

    def test_get_file_path(self):
        path1 = views.get_file_path("mykey1")
        path2 = views.get_file_path("mykey2")
        self.assertEqual(
            os.path.join(
                settings.ORA2_FILEUPLOAD_ROOT,
                settings.FILE_UPLOAD_STORAGE_BUCKET_NAME,
                "mykey1"
            ),
            os.path.dirname(path1)
        )
        self.assertNotEqual(path1, path2)

    def test_hack_get_file_path(self):
        expected_path = os.path.join(
            settings.ORA2_FILEUPLOAD_ROOT,
            settings.FILE_UPLOAD_STORAGE_BUCKET_NAME,
            "key",
            "content"
        )
        self.assertEqual(
            expected_path,
            os.path.abspath(views.get_file_path("../key"))
        )
        self.assertEqual(
            expected_path,
            os.path.abspath(views.get_file_path("../key/"))
        )
        self.assertEqual(
            expected_path,
            os.path.abspath(views.get_file_path(" ../key/ "))
        )

    def test_safe_save(self):
        self.assertRaises(
            exceptions.FileUploadRequestError,
            views.safe_save,
            "/tmp/nonauthorisedbucket/file.txt",
            "content"
        )

    def test_delete_file_data_on_metadata_saving_error(self):
        key = "key"
        file_path = views.get_file_path(key)
        non_existing_path = "/non/existing/path"

        with patch('openassessment.fileupload.views_filesystem.get_metadata_path') as mock_get_metadata_path:
            mock_get_metadata_path.return_value = non_existing_path
            self.assertRaises(
                exceptions.FileUploadRequestError,
                views.save_to_file,
                "key", "content", "metadata"
            )

        self.assertFalse(os.path.exists(file_path))
        self.assertFalse(os.path.exists(non_existing_path))

    @override_settings(ORA2_FILEUPLOAD_ROOT='')
    def test_undefined_file_upload_root(self):
        self.assertRaises(exceptions.FileUploadInternalError, views.get_file_path, self.key)

    @override_settings(ORA2_FILEUPLOAD_ROOT='/tmp/nonexistingdirectory')
    def test_file_upload_root_does_not_exist(self):
        if os.path.exists(settings.ORA2_FILEUPLOAD_ROOT):
            shutil.rmtree(settings.ORA2_FILEUPLOAD_ROOT)
        self.assertRaises(exceptions.FileUploadInternalError, views.save_to_file, self.key, "content")

    def test_post_is_405(self):
        upload_url = self.backend.get_upload_url(self.key, "bar")
        response = self.client.post(upload_url, data={"attachment": self.content})
        self.assertEqual(405, response.status_code)

    def test_metadata(self):
        self.content_type = "image/bmp"
        upload_url = self.backend.get_upload_url(self.key, self.content_type)

        self.client.put(upload_url, data=self.content.read(), content_type=self.content_type)
        metadata_path = views.get_metadata_path(self.key_name)
        metadata = json.load(open(metadata_path))

        self.assertIsNotNone(metadata_path)
        self.assertTrue(os.path.exists(metadata_path), "No metadata found at %s" % metadata_path)
        self.assertIn("Content-Type", metadata)
        self.assertIn("Date", metadata)
        self.assertIn("Content-MD5", metadata)
        self.assertIn("Content-Length", metadata)

    def test_upload_download(self):
        upload_url = self.backend.get_upload_url(self.key, self.content_type)
        download_url = self.backend.get_download_url(self.key)
        file_path = views.get_file_path(self.key_name)

        upload_response = self.client.put(upload_url, data=self.content.read(), content_type=self.content_type)
        download_response = self.client.get(download_url)
        self.content.seek(0)

        self.assertIn("/" + self.key, upload_url)
        self.assertEqual(200, upload_response.status_code)
        self.assertEqual("", upload_response.content)
        self.assertEqual(200, download_response.status_code)
        self.assertEqual(
            "attachment; filename=" + self.key,
            download_response.get('Content-Disposition')
        )
        self.assertEqual(self.content_type, download_response.get('Content-Type'))
        self.assertIn("foobar content", download_response.content)
        self.assertTrue(os.path.exists(file_path), "File %s does not exist" % file_path)
        with open(file_path) as f:
            self.assertEqual(self.content.read(), f.read())

    def test_download_content_with_no_content_type(self):
        views.save_to_file(self.key_name, "uploaded content", metadata=None)
        download_url = self.backend.get_download_url(self.key)

        download_response = self.client.get(download_url)
        self.assertEqual(200, download_response.status_code)
        self.assertEqual('application/octet-stream', download_response["Content-Type"])

    def test_upload_with_unauthorized_key(self):
        upload_url = reverse("openassessment-filesystem-storage", kwargs={'key': self.key_name})

        cache_before_request = get_filesystem_cache().get(self.key_name)
        upload_response = self.client.put(upload_url, data=self.content.read(), content_type=self.content_type)
        cache_after_request = get_filesystem_cache().get(self.key_name)
        self.assertIsNone(cache_before_request)
        self.assertEqual(404, upload_response.status_code)
        self.assertIsNone(cache_after_request)

    def test_download_url_with_unauthorized_key(self):
        download_url = reverse("openassessment-filesystem-storage", kwargs={'key': self.key_name})
        views.save_to_file(self.key_name, "uploaded content")
        download_response = self.client.get(download_url)

        self.assertEqual(404, download_response.status_code)

    def test_upload_download_with_accented_key(self):
        self.set_key(u"noël.jpg")
        upload_url = self.backend.get_upload_url(self.key, self.content_type)
        download_url = self.backend.get_download_url(self.key)

        upload_response = self.client.put(upload_url, data=self.content.read(), content_type=self.content_type)
        download_response = self.client.get(download_url)

        self.assertEqual(200, upload_response.status_code)
        self.assertEqual(200, download_response.status_code)
