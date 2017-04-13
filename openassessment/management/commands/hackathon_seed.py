"""
Managment command to take my data set and insert it as
"staff graded" assessments.
Hackathon 16 proof-of-concept, not intended for release.

This pairs with the ai_grading_hack task in edx-platform.
"""

from django.core.management.base import BaseCommand
from openassessment.assessment.api.staff import create_assessment
from optparse import make_option
from submissions import api as sub_api


class Command(BaseCommand):
    """
    It's a command
    """
    option_list = BaseCommand.option_list + (
        make_option('-b', '--block',
            metavar='BLOCK_ID',
            dest='location',
            default=False,
            help='Course ID for grade distribution'),
        make_option('-c', '--course',
            metavar='COURSE_ID',
            dest='course',
            default=False,
            help='Course ID for grade distribution')
        )

    def handle(self, *args, **options):
        with open("erics_hackathon_data.csv", "r") as infile:
            for line in open("/home/efischer19/sample_data.csv"):
                tokens = line.split('|')
                student_id = int(infile.readline())
                student_item = {
                    "student_id": student_id,
                    'course_id': options['course'],
                    'item_id': options['location'],
                    'item_type': 'openassessment'
                }
                answer = {"text": tokens[1]}
                submission = sub_api.create_submission(student_item, answer)

                _ = create_assessment(
                    submission['uuid'],
                    1,
                    self.points_to_option(tokens[2], tokens[3]),
                    {},
                    "Auto-generated",
                    self.rubric
                )

    def points_to_option(self, points1, points2):
        """
        Map a given points value to the correct option.
        """
        return {
            "dim1": self.rubric['criteria'][0]['options'][int(points1) - 1]['name'],
            "dim2": self.rubric['criteria'][0]['options'][int(points2) - 1]['name']
        }

    @property
    def rubric(self):
        """
        Rubric used to evaluate assessments. Specifically crafted for my test problem.
        """
        return {
            "criteria": [
                {
                    "name": "dim1",
                    "prompt": "dimension 1",
                    "options": [
                        {"name": "worst", "points": "1", "explanation": ""},
                        {"name": "bad", "points": "2", "explanation": ""},
                        {"name": "average", "points": "3", "explanation": ""},
                        {"name": "good", "points": "4", "explanation": ""},
                        {"name": "best", "points": "5", "explanation": ""}
                    ]
                },
                {
                    "name": "dim2",
                    "prompt": "dimension 2",
                    "options": [
                        {"name": "worst", "points": "1", "explanation": ""},
                        {"name": "bad", "points": "2", "explanation": ""},
                        {"name": "average", "points": "3", "explanation": ""},
                        {"name": "good", "points": "4", "explanation": ""},
                        {"name": "best", "points": "5", "explanation": ""}
                    ]
                }
            ]
        }
