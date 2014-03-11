"""
Create dummy submissions and assessments for testing.
"""
import copy
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
import loremipsum
from submissions import api as sub_api
from openassessment.workflow import api as workflow_api
from openassessment.assessment import peer_api, self_api



class Command(BaseCommand):
    """
    Create dummy submissions and assessments for testing.
    This will generate fake (lorem ipsum) data for:
        * Submission response text
        * Assessment rubric definition
        * Assessment rubric scores
        * Assessment feedback
    """

    help = 'Create dummy submissions and assessments'
    args = '<USER_ID> <COURSE_ID> <ITEM_ID>'

    option_list = BaseCommand.option_list + (
        make_option(
            '-p', '--peer-assessments', dest='num_peer_assessments',
            action='store', default=0, type=int,
            help='Number of peer assessments to create for the submission'
        ),
        make_option(
            '-s', '--self-assessment', dest='has_self_assessment',
            action='store_true', default=False,
            help='If true, create a self-assessment for the submission'
        ),
    )

    REQUIRED_NUM_ARGS = 3

    DUMMY_RUBRIC = {
        'criteria': [
            {
                'name': "Ideas",
                'prompt': "Determine if there is a unifying theme or main idea.",
                'order_num': 0,
                'options': [
                    {
                        'order_num': 0, 'points': 0, 'name': 'Poor',
                        'explanation': """Difficult for the reader to discern the main idea.
                        Too brief or too repetitive to establish or maintain a focus."""
                    },
                    {
                        'order_num': 1, 'points': 3, 'name': 'Fair',
                        'explanation': """Presents a unifying theme or main idea, but may
                        include minor tangents.  Stays somewhat focused on topic and
                        task."""
                    },
                    {
                        'order_num': 2, 'points': 5, 'name': 'Good',
                        'explanation': """Presents a unifying theme or main idea without going
                        off on tangents.  Stays completely focused on topic and task."""
                    },
                ],
            },
            {
                'name': "Content",
                'prompt': "Assess the content of the submission",
                'order_num': 1,
                'options': [
                    {
                        'order_num': 0, 'points': 0, 'name': 'Poor',
                        'explanation': """Includes little information with few or no details or
                        unrelated details.  Unsuccessful in attempts to explore any
                        facets of the topic."""
                    },
                    {
                        'order_num': 1, 'points': 1, 'name': 'Fair',
                        'explanation': """Includes little information and few or no details.
                        Explores only one or two facets of the topic."""
                    },
                    {
                        'order_num': 2, 'points': 3, 'name': 'Good',
                        'explanation': """Includes sufficient information and supporting
                        details. (Details may not be fully developed; ideas may be
                        listed.)  Explores some facets of the topic."""
                    },
                    {
                        'order_num': 3, 'points': 3, 'name': 'Excellent',
                        'explanation': """Includes in-depth information and exceptional
                        supporting details that are fully developed.  Explores all
                        facets of the topic."""
                    },
                ],
            },
        ]
    }

    def handle(self, *args, **options):
        """
        Execute the command.

        Args:
            user_id (str): Unique ID of the user creating the submission.
            course_id (str): Unique ID of the course in which to create the submission.
            item_id (str): Unique ID of the item in the course for which to create the submission.

        Kwargs:
            num_peer_assessments (int): Number of peer assessments to create for the submission.
            has_self_assessment (bool): If true, create a self-assessment for the submission.
        """

        # Verify that we have the correct number of positional args
        if len(args) < self.REQUIRED_NUM_ARGS:
            raise CommandError('Usage: create_oa_submission <USER_ID> <COURSE_ID> <ITEM_ID>')

        # Create the submission
        student_item = {
            'student_id': args[0],
            'course_id': args[1],
            'item_id': args[2],
            'item_type': 'openassessment'
        }
        submission_uuid = self._create_dummy_submission(student_item)

        # Create peer assessments
        for num in range(options['num_peer_assessments']):
            scorer_id = 'test_{num}'.format(num=num)

            # The scorer needs to make a submission before assessing
            scorer_student_item = copy.copy(student_item)
            scorer_student_item['student_id'] = scorer_id
            self._create_dummy_submission(scorer_student_item)

            # Retrieve the submission we want to score
            # Note that we are NOT using the priority queue here, since we know
            # exactly which submission we want to score.
            peer_api.create_peer_workflow_item(scorer_id, submission_uuid)

            # Create the peer assessment
            assessment = {
                'options_selected': {'Ideas': 'Poor', 'Content': 'Good'},
                'feedback': loremipsum.get_paragraphs(2)
            }
            peer_api.create_assessment(submission_uuid, scorer_id, assessment, self.DUMMY_RUBRIC)

        # Create self-assessment
        if options['has_self_assessment']:
            self_api.create_assessment(
                submission_uuid, student_item['student_id'],
                {'Ideas': 'Good', 'Content': 'Excellent'},
                self.DUMMY_RUBRIC
            )

    def _create_dummy_submission(self, student_item):
        """
        Create a dummy submission for a student.

        Args:
            student_item (dict): Serialized StudentItem model.

        Returns:
            str: submission UUID
        """
        submission = sub_api.create_submission(student_item, loremipsum.get_paragraphs(5))
        workflow_api.create_workflow(submission['uuid'])
        workflow_api.update_from_assessments(
            submission['uuid'], {'peer': {'must_grade': 1, 'must_be_graded_by': 1}}
        )
        return submission['uuid']