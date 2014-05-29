# -*- coding: utf-8 -*-
"""
Simulate failure of the worker AI grading tasks.
When the workers fail to successfully complete AI grading,
the AI grading workflow in the database will never be marked complete.

To simulate the error condition, therefore, we create incomplete
AI grading workflows without scheduling a grading task.

To recover, a staff member can reschedule incomplete grading tasks.

"""
from django.core.management.base import BaseCommand, CommandError
from submissions import api as sub_api
from openassessment.assessment.models import AIGradingWorkflow, AIClassifierSet
from openassessment.assessment.serializers import rubric_from_dict


class Command(BaseCommand):
    """
    Create submissions and AI incomplete grading workflows.
    """

    help = (
        u"Simulate failure of the worker AI grading tasks "
        u"by creating incomplete AI grading workflows in the database."
    )

    args = '<COURSE_ID> <PROBLEM_ID> <NUM_SUBMISSIONS>'

    RUBRIC_OPTIONS = [
        {
            "order_num": 0,
            "name": u"poor",
            "explanation": u"Poor job!",
            "points": 0,
        },
        {
            "order_num": 1,
            "name": u"good",
            "explanation": u"Good job!",
            "points": 1,
        }
    ]

    RUBRIC = {
        'prompt': u"Test prompt",
        'criteria': [
            {
                "order_num": 0,
                "name": u"vocabulary",
                "prompt": u"Vocabulary",
                "options": RUBRIC_OPTIONS
            },
            {
                "order_num": 1,
                "name": u"grammar",
                "prompt": u"Grammar",
                "options": RUBRIC_OPTIONS
            }
        ]
    }

    # Since we're not actually running an AI scoring algorithm,
    # we can use dummy data for the classifier, as long as it's
    # JSON-serializable.
    CLASSIFIERS = {
        u'vocabulary': {},
        u'grammar': {}
    }

    ALGORITHM_ID = u'fake'
    STUDENT_ID = u'test_student'
    ANSWER = {'answer': 'test answer'}

    def handle(self, *args, **options):
        """
        Execute the command.

        Args:
            course_id (unicode): The ID of the course to create submissions/workflows in.
            item_id (unicode): The ID of the problem in the course.
            num_submissions (int): The number of submissions/workflows to create.

        Raises:
            CommandError

        """
        if len(args) < 3:
            raise CommandError(u"Usage: simulate_ai_grading_error {}".format(self.args))

        # Parse arguments
        course_id = args[0].decode('utf-8')
        item_id = args[1].decode('utf-8')
        num_submissions = int(args[2])

        # Create the rubric model
        rubric = rubric_from_dict(self.RUBRIC)

        # Create the classifier set
        classifier_set = AIClassifierSet.create_classifier_set(
            self.CLASSIFIERS, rubric, self.ALGORITHM_ID
        )

        # Create submissions and grading workflows
        for num in range(num_submissions):
            student_item = {
                'course_id': course_id,
                'item_id': item_id,
                'item_type': 'openassessment',
                'student_id': "{base}_{num}".format(base=self.STUDENT_ID, num=num)
            }
            submission = sub_api.create_submission(student_item, self.ANSWER)
            workflow = AIGradingWorkflow.start_workflow(
                submission['uuid'], self.RUBRIC, self.ALGORITHM_ID
            )
            workflow.classifier_set = classifier_set
            workflow.save()
            print u"{num}: Created incomplete grading workflow with UUID {uuid}".format(
                num=num, uuid=workflow.uuid
            )
