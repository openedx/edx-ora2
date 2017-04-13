"""
Managment command to take my data set and insert it as
"staff graded" assessments.
Hackathon 16 proof-of-concept, not intended for release.

This pairs with the ai_grading_hack task in edx-platform.
"""

from django.core.management.base import BaseCommand
from openassessment.assessment.api.staff import create_assessment
from submissions import api as sub_api


class Command(BaseCommand):
    """
    It's a command
    """
    def handle(self, *args, **options):
        with open("erics_hackathon_data.csv", "r") as infile:
            for line in open(args[0]):
                tokens = line.split('|')
                student_id = int(infile.readline())
                student_item = {
                    "student_id": student_id,
                    'course_id': args[1],
                    'item_id': args[2],
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
        option1 = ""
        option2 = ""
        for i in range(1, 5):
            if i == points1:
                option1 = self.rubric['criteria'][0]['options'][i - 1]['name']
            if i == points2:
                option2 = self.rubric['criteria'][0]['options'][i - 1]['name']
        return {
            "dim1": option1,
            "dim2": option2
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
