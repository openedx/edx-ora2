"""
Generate CSV files for submission and assessment data, then upload to S3.
"""
from __future__ import absolute_import, print_function

import datetime
import os
import os.path
import shutil
import sys
import tarfile
import tempfile

import six

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

import boto
from boto.s3.key import Key
from openassessment.data import CsvWriter


class Command(BaseCommand):
    """
    Create and upload CSV files for submission and assessment data.
    """

    help = 'Create and upload CSV files for submission and assessment data.'
    args = '<COURSE_ID> <S3_BUCKET_NAME>'

    OUTPUT_CSV_PATHS = {
        output_name: "{}.csv".format(output_name)
        for output_name in CsvWriter.MODELS
    }

    URL_EXPIRATION_HOURS = 24
    PROGRESS_INTERVAL = 10

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self._history = list()
        self._submission_counter = 0

    @property
    def history(self):
        """
        Return the upload history, which is useful for testing.

        Returns:
            list of dictionaries with keys 'url' and 'key'

        """
        return self._history

    def handle(self, *args, **options):
        """
        Execute the command.

        Args:
            course_id (unicode): The ID of the course to use.
            s3_bucket_name (unicode): The name of the S3 bucket to upload to.

        Raises:
            CommandError

        """
        if len(args) < 2:
            raise CommandError(u'Usage: upload_oa_data {}'.format(self.args))

        course_id, s3_bucket = args[0], args[1]
        if isinstance(course_id, bytes):
            course_id = course_id.decode('utf-8')
        if isinstance(s3_bucket, bytes):
            s3_bucket = s3_bucket.decode('utf-8')
        csv_dir = tempfile.mkdtemp()

        try:
            print(u"Generating CSV files for course '{}'".format(course_id))
            self._dump_to_csv(course_id, csv_dir)
            print(u"Creating archive of CSV files in {}".format(csv_dir))
            archive_path = self._create_archive(csv_dir)
            print(u"Uploading {} to {}/{}".format(archive_path, s3_bucket, course_id))
            url = self._upload(course_id, archive_path, s3_bucket)
            print("== Upload successful ==")
            print(u"Download URL (expires in {} hours):\n{}".format(self.URL_EXPIRATION_HOURS, url))
        finally:
            # Assume that the archive was created in the directory,
            # so to clean up we just need to delete the directory.
            shutil.rmtree(csv_dir)

    def _dump_to_csv(self, course_id, csv_dir):
        """
        Create CSV files for submission/assessment data in a directory.

        Args:
            course_id (unicode): The ID of the course to dump data from.
            csv_dir (unicode): The absolute path to the directory in which to create CSV files.

        Returns:
            None
        """
        output_streams = {
            name: open(os.path.join(csv_dir, rel_path), 'w')
            for name, rel_path in six.iteritems(self.OUTPUT_CSV_PATHS)
        }
        csv_writer = CsvWriter(output_streams, self._progress_callback)
        csv_writer.write_to_csv(course_id)

    def _create_archive(self, dir_path):
        """
        Create an archive of a directory.

        Args:
            dir_path (unicode): The absolute path to the directory containing the CSV files.

        Returns:
            unicode: Absolute path to the archive.

        """
        tarball_name = u"{}.tar.gz".format(
            datetime.datetime.utcnow().strftime("%Y-%m-%dT%H_%M")
        )
        tarball_path = os.path.join(dir_path, tarball_name)
        with tarfile.open(tarball_path, "w:gz") as tar:
            for rel_path in self.OUTPUT_CSV_PATHS.values():
                tar.add(os.path.join(dir_path, rel_path), arcname=rel_path)
        return tarball_path

    def _upload(self, course_id, file_path, s3_bucket):
        """
        Upload a file.

        Args:
            course_id (unicode): The ID of the course.
            file_path (unicode): Absolute path to the file to upload.
            s3_bucket (unicode): Name of the S3 bucket where the file will be uploaded.

        Returns:
            str: URL to access the uploaded archive.

        """
        # Try to get the AWS credentials from settings if they are available
        # If not, these will default to `None`, and boto will try to use
        # environment vars or configuration files instead.
        aws_access_key_id = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
        aws_secret_access_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
        conn = boto.connect_s3(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )

        bucket = conn.get_bucket(s3_bucket)
        key_name = os.path.join(course_id, os.path.split(file_path)[1])
        key = Key(bucket=bucket, name=key_name)
        key.set_contents_from_filename(file_path)
        url = key.generate_url(self.URL_EXPIRATION_HOURS * 3600)

        # Store the key and url in the history
        self._history.append({'key': key_name, 'url': url})

        return url

    def _progress_callback(self):
        """
        Indicate progress to the user as submissions are processed.
        """
        self._submission_counter += 1
        if self._submission_counter > 0 and self._submission_counter % self.PROGRESS_INTERVAL == 0:
            sys.stdout.write('.')
            sys.stdout.flush()
