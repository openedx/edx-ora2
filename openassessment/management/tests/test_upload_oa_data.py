# -*- coding: utf-8 -*-
"""
Tests for management command that uploads submission/assessment data.
"""
from StringIO import StringIO
import tarfile
from django.test import TestCase
import boto
import moto
from openassessment.management.commands import upload_oa_data
from openassessment.workflow import api as workflow_api
from submissions import api as sub_api


class UploadDataTest(TestCase):
    """
    Test the upload management command.  Archiving and upload are in-scope,
    but the contents of the generated CSV files are tested elsewhere.
    """

    COURSE_ID = u"TɘꙅT ↄoUᴙꙅɘ"
    BUCKET_NAME = u"com.example.data"
    CSV_NAMES = [
        "assessment.csv", "assessment_part.csv",
        "assessment_feedback.csv", "assessment_feedback_option.csv",
        "submission.csv", "score.csv",
    ]

    @moto.mock_s3
    def test_upload(self):
        # Create an S3 bucket using the fake S3 implementation
        conn = boto.connect_s3()
        conn.create_bucket(self.BUCKET_NAME)

        # Create some submissions to ensure that we cover
        # the progress indicator code.
        for index in range(50):
            student_item = {
                'student_id': "test_user_{}".format(index),
                'course_id': self.COURSE_ID,
                'item_id': 'test_item',
                'item_type': 'openassessment',
            }
            submission_text = "test submission {}".format(index)
            submission = sub_api.create_submission(student_item, submission_text)
            workflow_api.create_workflow(submission['uuid'], ['peer', 'self'])

        # Create and upload the archive of CSV files
        # This should generate the files even though
        # we don't have any data available.
        cmd = upload_oa_data.Command()
        cmd.handle(self.COURSE_ID.encode('utf-8'), self.BUCKET_NAME)

        # Retrieve the uploaded file from the fake S3 implementation
        self.assertEqual(len(cmd.history), 1)
        bucket = conn.get_all_buckets()[0]
        key = bucket.get_key(cmd.history[0]['key'])
        contents = StringIO(key.get_contents_as_string())

        # Expect that the contents contain all the expected CSV files
        with tarfile.open(mode="r:gz", fileobj=contents) as tar:
            file_sizes = {
                member.name: member.size
                for member in tar.getmembers()
            }
            for csv_name in self.CSV_NAMES:
                self.assertIn(csv_name, file_sizes)
                self.assertGreater(file_sizes[csv_name], 0)

        # Expect that we generated a URL for the bucket
        url = cmd.history[0]['url']
        self.assertIn("https://{}".format(self.BUCKET_NAME), url)
