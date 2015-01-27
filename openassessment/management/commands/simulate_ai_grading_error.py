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
from openassessment.assessment.worker.algorithm import AIAlgorithm


class Command(BaseCommand):
    """
    Create submissions and AI incomplete grading workflows.
    """

    help = (
        u"Simulate failure of the worker AI grading tasks "
        u"by creating incomplete AI grading workflows in the database."
    )

    args = '<COURSE_ID> <PROBLEM_ID> <NUM_SUBMISSIONS> <ALGORITHM_ID>'

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
        'prompts': [{"description": u"Test prompt"}],
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

    EXAMPLES = {
        "vocabulary": [
            AIAlgorithm.ExampleEssay(
                text=u"World Food Day is celebrated every year around the world on 16 October in honor "
                u"of the date of the founding of the Food and Agriculture "
                u"Organization of the United Nations in 1945.",
                score=0
            ),
            AIAlgorithm.ExampleEssay(
                text=u"Since 1981, World Food Day has adopted a different theme each year "
                u"in order to highlight areas needed for action and provide a common focus.",
                score=1
            ),
        ],
        "grammar": [
            AIAlgorithm.ExampleEssay(
                text=u"Most of the themes revolve around agriculture because only investment in agriculture ",
                score=0
            ),
            AIAlgorithm.ExampleEssay(
                text=u"In spite of the importance of agriculture as the driving force "
                u"in the economies of many developing countries, this "
                u"vital sector is frequently starved of investment.",
                score=1
            )
        ]
    }

    STUDENT_ID = u'test_student'
    ANSWER = {"text": 'test answer'}

    def handle(self, *args, **options):
        """
        Execute the command.

        Args:
            course_id (unicode): The ID of the course to create submissions/workflows in.
            item_id (unicode): The ID of the problem in the course.
            num_submissions (int): The number of submissions/workflows to create.
            algorithm_id (unicode): The ID of the ML algorithm to use ("fake" or "ease")

        Raises:
            CommandError

        """
        if len(args) < 4:
            raise CommandError(u"Usage: simulate_ai_grading_error {}".format(self.args))

        # Parse arguments
        course_id = args[0].decode('utf-8')
        item_id = args[1].decode('utf-8')
        num_submissions = int(args[2])
        algorithm_id = args[3].decode('utf-8')

        # Create the rubric model
        rubric = rubric_from_dict(self.RUBRIC)

        # Train classifiers
        print u"Training classifiers using {algorithm_id}...".format(algorithm_id=algorithm_id)
        algorithm = AIAlgorithm.algorithm_for_id(algorithm_id)
        classifier_data = {
            criterion_name: algorithm.train_classifier(example)
            for criterion_name, example in self.EXAMPLES.iteritems()
        }
        print u"Successfully trained classifiers."

        # Create the classifier set
        classifier_set = AIClassifierSet.create_classifier_set(
            classifier_data, rubric, algorithm_id, course_id, item_id
        )
        print u"Successfully created classifier set with id {}".format(classifier_set.pk)

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
                submission['uuid'], self.RUBRIC, algorithm_id
            )
            workflow.classifier_set = classifier_set
            workflow.save()
            print u"{num}: Created incomplete grading workflow with UUID {uuid}".format(
                num=num, uuid=workflow.uuid
            )
