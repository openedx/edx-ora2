# -*- coding: utf-8 -*-
"""
Tests for openassessment data aggregation.
"""

import os.path
from StringIO import StringIO
import csv
from django.core.management import call_command
import ddt
from openassessment.test_utils import CacheResetTest
from submissions import api as sub_api
from openassessment.workflow import api as workflow_api
from openassessment.data import CsvWriter


@ddt.ddt
class CsvWriterTest(CacheResetTest):
    """
    Test for writing openassessment data to CSV.
    """
    longMessage = True
    maxDiff = None

    @ddt.file_data('data/write_to_csv.json')
    def test_write_to_csv(self, data):
        # Create in-memory buffers for the CSV file data
        output_streams = self._output_streams(data['expected_csv'].keys())

        # Load the database fixture
        # We use the database fixture to ensure that this test will
        # catch backwards-compatibility issues even if the Django model
        # implementation or API calls change.
        self._load_fixture(data['fixture'])

        # Write the data to CSV
        writer = CsvWriter(output_streams)
        writer.write_to_csv(data['course_id'])

        # Check that the CSV matches what we expected
        for output_name, expected_csv in data['expected_csv'].iteritems():
            output_buffer = output_streams[output_name]
            output_buffer.seek(0)
            actual_csv = csv.reader(output_buffer)
            for expected_row in expected_csv:
                try:
                    actual_row = actual_csv.next()
                except StopIteration:
                    actual_row = None
                self.assertEqual(
                    actual_row, expected_row,
                    msg="Output name: {}".format(output_name)
                )

            # Check for extra rows
            try:
                extra_row = actual_csv.next()
            except StopIteration:
                extra_row = None

            if extra_row is not None:
                self.fail(u"CSV contains extra row: {}".format(extra_row))

    def test_many_submissions(self):
        # Create a lot of submissions
        num_submissions = 234
        for index in range(num_submissions):
            student_item = {
                'student_id': "test_user_{}".format(index),
                'course_id': 'test_course',
                'item_id': 'test_item',
                'item_type': 'openassessment',
            }
            submission_text = "test submission {}".format(index)
            submission = sub_api.create_submission(student_item, submission_text)
            workflow_api.create_workflow(submission['uuid'])

        # Generate a CSV file for the submissions
        output_streams = self._output_streams(['submission'])
        writer = CsvWriter(output_streams)
        writer.write_to_csv('test_course')

        # Parse the generated CSV
        content = output_streams['submission'].getvalue()
        rows = content.split('\n')

        # Remove the first row (header) and last row (blank line)
        rows = rows[1:-1]

        # Check that we have the right number of rows
        self.assertEqual(len(rows), num_submissions)

    def test_other_course_id(self):
        # Try a course ID with no submissions
        self._load_fixture('db_fixtures/scored.json')
        output_streams = self._output_streams(CsvWriter.MODELS)
        writer = CsvWriter(output_streams)
        writer.write_to_csv('other_course')

        # Expect that each output has only two lines (the header and a blank line)
        # since this course has no submissions
        for output in output_streams.values():
            content = output.getvalue()
            rows = content.split('\n')
            self.assertEqual(len(rows), 2)

    def test_unicode(self):
        # Flush out unicode errors
        self._load_fixture('db_fixtures/unicode.json')
        output_streams = self._output_streams(CsvWriter.MODELS)
        CsvWriter(output_streams).write_to_csv(u"𝓽𝓮𝓼𝓽_𝓬𝓸𝓾𝓻𝓼𝓮")

        # Check that data ended up in the reports
        for output in output_streams.values():
            content = output.getvalue()
            rows = content.split('\n')
            self.assertGreater(len(rows), 2)

    def _output_streams(self, names):
        """
        Create in-memory buffers.

        Args:
            names (list of unicode): The output names.

        Returns:
            dict: map of output names to StringIO objects.

        """
        output_streams = dict()

        for output_name in names:
            output_buffer = StringIO()
            self.addCleanup(output_buffer.close)
            output_streams[output_name] = output_buffer

        return output_streams

    def _load_fixture(self, fixture_relpath):
        """
        Load a database fixture into the test database.

        Args:
            fixture_relpath (unicode): Path to the fixture,
                relative to the test/data directory.

        Returns:
            None
        """
        fixture_path = os.path.join(
            os.path.dirname(__file__), 'data', fixture_relpath
        )
        print "Loading database fixtures from {}".format(fixture_path)
        call_command('loaddata', fixture_path)
