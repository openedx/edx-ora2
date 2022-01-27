"""
Django models specific to the student training assessment type.
"""

from django.db import IntegrityError, models, transaction
from django.utils import timezone

from submissions import api as sub_api

from .training import TrainingExample


class StudentTrainingWorkflow(models.Model):
    """
    Tracks a student's progress through the student training assessment step.
    """
    # The submission UUID of the student being trained
    submission_uuid = models.CharField(max_length=128, db_index=True, unique=True)

    # Information about the student and problem
    # This duplicates information associated with the submission itself,
    # but we include it here to make it easier to query workflows.
    # Since submissions are immutable, we can do this without
    # jeopardizing data integrity.
    student_id = models.CharField(max_length=40, db_index=True)
    item_id = models.CharField(max_length=128, db_index=True)
    course_id = models.CharField(max_length=255, db_index=True)

    class Meta:
        app_label = "assessment"

    @classmethod
    def create_workflow(cls, submission_uuid):
        """
        Create a student training workflow.

        Args:
            submission_uuid (str): The UUID of the submission from the student
                being trained.

        Returns:
            StudentTrainingWorkflow

        Raises:
            SubmissionError: There was an error retrieving the submission.

        """
        # Retrieve the student item info
        submission = sub_api.get_submission_and_student(submission_uuid)
        student_item = submission['student_item']

        # Create the workflow
        workflow = None
        try:
            workflow, __ = cls.objects.get_or_create(
                submission_uuid=submission_uuid,
                student_id=student_item['student_id'],
                item_id=student_item['item_id'],
                course_id=student_item['course_id']
            )
        # If we get an integrity error, it means we've violated a uniqueness constraint
        # (someone has created this object after we checked if it existed)
        # We can therefore assume that the object exists and do nothing.
        except IntegrityError:
            pass
        return workflow

    @classmethod
    def get_workflow(cls, submission_uuid):
        """
        Get a student training workflow.

        Args:
            submission_uuid (str): The UUID of the submission from the student
                being trained.

        Returns:
            StudentTrainingWorkflow. None if no workflow is found.

        """
        try:
            return cls.objects.get(submission_uuid=submission_uuid)
        except cls.DoesNotExist:
            return None

    @property
    def num_completed(self):
        """
        Return the number of training examples that the
        student successfully assessed.

        Returns:
            int

        """
        return self.items.filter(completed_at__isnull=False).count()

    def next_training_example(self, examples):
        """
        Return the next training example for the student to assess.
        If the student is already working on an example, return that.
        Otherwise, choose an example the student hasn't seen
        from the list of available examples.

        Args:
            examples (list of TrainingExample): Training examples to choose from.

        Returns:
            TrainingExample or None

        """
        # Fetch all the items for this workflow from the database
        # Since Django's `select_related` does not follow reverse keys
        # we perform the filter ourselves.
        items = StudentTrainingWorkflowItem.objects.select_related(
            'training_example'
        ).filter(workflow=self)

        # If we're already working on an item, then return that item
        incomplete_items = [item for item in items if not item.is_complete]
        if incomplete_items:
            return incomplete_items[0].training_example

        # Otherwise, pick an item that we have not completed
        # from the list of examples.
        completed_examples = [
            item.training_example for item in items
        ]
        available_examples = [
            available for available in examples
            if available not in completed_examples
        ]

        # If there are no more items available, return None
        if not available_examples:
            return None
        # Otherwise, create a new workflow item for the example
        # and add it to the workflow
        order_num = len(items) + 1
        next_example = available_examples[0]

        try:
            with transaction.atomic():
                StudentTrainingWorkflowItem.objects.create(
                    workflow=self,
                    order_num=order_num,
                    training_example=next_example
                )
        # If we get an integrity error, it means we've violated a uniqueness constraint
        # (someone has created this object after we checked if it existed)
        # Since the object already exists, we don't need to do anything
        # Use the example passed into the function, because attempting to
        # retrieve the stored example would result in an race condition.
        except IntegrityError:
            pass
        return next_example

    @property
    def current_item(self):
        """
        Return the item the student is currently working on,
        or None.

        Returns:
            StudentTrainingWorkflowItem or None

        """
        next_incomplete = self.items.select_related(
            'training_example'
        ).filter(
            completed_at__isnull=True
        ).order_by('order_num')[:1]

        return None if not next_incomplete else next_incomplete[0]


class StudentTrainingWorkflowItem(models.Model):
    """
    A particular step in the training workflow.  At each step,
    a student must try assessing an example submission.

    If the student gives the same scores as the instructor,
    then the student proceeds to the next example;
    if there are no examples left, the student has
    successfully completed training.
    """
    workflow = models.ForeignKey(StudentTrainingWorkflow, related_name="items", on_delete=models.CASCADE)
    order_num = models.PositiveIntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(default=None, null=True)
    training_example = models.ForeignKey(TrainingExample, on_delete=models.CASCADE)

    class Meta:
        app_label = "assessment"
        ordering = ["workflow", "order_num"]
        unique_together = ('workflow', 'order_num')

    @property
    def is_complete(self):
        """
        Check whether the student has completed this workflow item.

        Returns:
            bool

        """
        return self.completed_at is not None

    def mark_complete(self):
        """
        Mark the item as complete.  Once an item is marked complete,
        it should stay complete!

        Returns:
            None

        """
        self.completed_at = timezone.now()
        self.save()

    def check_options(self, options_selected):
        """
        Compare the options that the student selected to
        the options set by the instructor in the training example.

        Args:
            options_selected (dict): Mapping of criterion names to option names.

        Returns:
            dict

        Example usage:
            >>> item.check_options({'vocabulary': 'good', 'grammar': 'poor'})
            {'vocabulary': 'excellent'}
            >>> item.check_options({'vocabulary': 'excellent', 'grammar': 'poor'})
            {}

        """
        staff_selected = self.training_example.options_selected_dict
        corrections = {}

        for criterion_name, option_name in staff_selected.items():
            missing_option = criterion_name not in options_selected
            incorrect_option = options_selected[criterion_name] != option_name

            if missing_option or incorrect_option:
                corrections[criterion_name] = option_name

        return corrections
