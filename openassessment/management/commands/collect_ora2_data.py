"""
Command to retrieve all ORA2 data for a course in a .csv.


This command differs from upload_oa_data in that it places all the data into one file.

Generates the same format as the instructor dashboard downloads.
"""


import csv
import os

from django.core.management.base import BaseCommand, CommandError

from openassessment.data import OraAggregateData


class Command(BaseCommand):
    """
    Query aggregated open assessment data, write to .csv
    """

    help = ("Usage: collect_ora2_data <course_id> --output-dir=<output_dir>")

    def add_arguments(self, parser):
        parser.add_argument('course_id', nargs='+', type=str)
        parser.add_argument(
            '-o',
            '--output-dir',
            action='store',
            dest='output_dir',
            default=None,
            help="Write output to a directory rather than stdout"
        )
        parser.add_argument(
            '-n',
            '--file-name',
            action='store',
            dest='file_name',
            default=None,
            help="Write CSV file to the given name"
        )

    def handle(self, *args, **options):
        """
        Run the command.
        """
        if not options['course_id']:
            raise CommandError("Course ID must be specified to fetch data")

        course_id = options['course_id']

        if options['file_name']:
            file_name = options['file_name']
        else:
            file_name = ("%s-ora2.csv" % course_id).replace("/", "-")

        if options['output_dir']:
            csv_file = open(os.path.join(options['output_dir'], file_name), 'wb')
        else:
            csv_file = self.stdout

        writer = csv.writer(csv_file, dialect='excel', quotechar='"', quoting=csv.QUOTE_ALL)

        header, rows = OraAggregateData.collect_ora2_data(course_id)

        writer.writerow(header)
        for row in rows:
            writer.writerow(_encode_row(row))


def _encode_row(data_list):
    """
    Properly encode ora2 responses for transcription into a .csv
    """
    processed_row = []

    for item in data_list:
        new_item = str(item)
        processed_row.append(new_item)

    return processed_row
