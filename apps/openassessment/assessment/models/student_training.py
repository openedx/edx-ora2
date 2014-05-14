"""
Django models specific to the student training assessment type.
"""
from django.db import models, transaction
from django.utils import timezone
from submissions import api as sub_api
from .training import TrainingExample


class StudentTrainingWorkflow(models.Model):
    """
    Tracks a student's progress through the student training assessment step.
    """
    # The submission UUID of the student being trained
    submission_uuid = models.CharField(max_length=128, db_index=True)

    # Information about the student and problem
    # This duplicates information associated with the submission itself,
    # but we include it here to make it easier to query workflows.
    # Since submissions are immutable, we can do this without
    # jeopardizing data integrity.
    student_id = models.CharField(max_length=40, db_index=True)
    item_id = models.CharField(max_length=128, db_index=True)
    course_id = models.CharField(max_length=40, db_index=True)

    class Meta:
        app_label = "assessment"

    @classmethod
    def get_or_create_workflow(cls, submission_uuid):
        """
        Create a student training workflow.

        Args:
            submission_uuid (str): The UUID of the submission from the student being trained.

        Returns:
            StudentTrainingWorkflow

        Raises:
            SubmissionError: There was an error retrieving the submission.

        """
        # Try to retrieve an existing workflow
        # If we find one, return it immediately
        try:
            return cls.objects.get(submission_uuid=submission_uuid)   # pylint:disable=E1101
        except cls.DoesNotExist:
            pass

        # Retrieve the student item info
        submission = sub_api.get_submission_and_student(submission_uuid)
        student_item = submission['student_item']

        # Create the workflow
        return cls.objects.create(
            submission_uuid=submission_uuid,
            student_id=student_item['student_id'],
            item_id=student_item['item_id'],
            course_id=student_item['course_id']
        )

    @transaction.commit_on_success
    def create_workflow_item(self, training_example):
        """
        Create a workflow item for a training example
        and add it to the workflow.

        Args:
            training_example (TrainingExample): The training example model
                associated with the next workflow item.

        Returns:
            StudentTrainingWorkflowItem

        """
        order_num = self.items.count() + 1  # pylint:disable=E1101
        item = StudentTrainingWorkflowItem.objects.create(
            workflow=self,
            order_num=order_num,
            training_example=training_example
        )
        self.items.add(item)    # pylint:disable=E1101
        self.save()
        return item

    @property
    def status(self):
        """
        The student's status within the workflow (num steps completed / num steps available).

        Returns:
            tuple of `(num_completed, num_total)`, both integers

        """
        items = self.items.all()    # pylint:disable=E1101
        num_complete = sum([1 if item.is_complete else 0 for item in items])
        num_total = len(items)
        return num_complete, num_total

    @property
    def num_completed(self):
        """
        Return the number of training examples that the
        student successfully assessed.

        Returns:
            int

        """
        return self.items.filter(completed_at__isnull=False).count()  # pylint:disable=E1101

    def next_incomplete_item(self, examples):
        """
        Find the next incomplete item in the workflow.

        Args:
            examples (list of TrainingExample): Training examples to choose from.

        Returns:
            StudentTrainingWorkflowItem or None

        """
        # If we're already working on an item, then return that item
        current_item = self.current_item
        if current_item is not None:
            return current_item

        # Otherwise, pick an item that we have not completed
        # from the list of examples.
        completed_examples = [
            item.training_example for item in self.items.all()  # pylint:disable=E1101
        ]
        available_examples = [
            available for available in examples
            if available not in completed_examples
        ]

        # If there are no more items available, return None
        if len(available_examples) == 0:
            return None
        # Otherwise, create a new workflow item for the example
        # and add it to the workflow
        else:
            return self.create_workflow_item(available_examples[0])

    @property
    def current_item(self):
        """
        Return the item the student is currently working on,
        or None.

        Returns:
            StudentTrainingWorkflowItem or None

        """
        next_incomplete = self.items.filter(  # pylint:disable=E1101
            completed_at__isnull=True
        ).order_by('order_num')[:1]

        if len(next_incomplete) > 0:
            return next_incomplete[0]
        else:
            return None


class StudentTrainingWorkflowItem(models.Model):
    """
    A particular step in the training workflow.  At each step,
    a student must try assessing an example submission.

    If the student gives the same scores as the instructor,
    then the student proceeds to the next example;
    if there are no examples left, the student has
    successfully completed training.
    """
    workflow = models.ForeignKey(StudentTrainingWorkflow, related_name="items")
    order_num = models.PositiveIntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(default=None, null=True)
    training_example = models.ForeignKey(TrainingExample)

    class Meta:
        app_label = "assessment"
        ordering = ["workflow", "order_num"]

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

    def check(self, options_selected):
        """
        Compare the options that the student selected to
        the options set by the instructor in the training example.

        Args:
            options_selected (dict): Mapping of criterion names to option names.

        Returns:
            dict

        Example usage:
            >>> item.check({'vocabulary': 'good', 'grammar': 'poor'})
            {'vocabulary': 'excellent'}
            >>> item.check({'vocabulary': 'excellent', 'grammar': 'poor'})
            {}

        """
        staff_selected = self.training_example.options_selected_dict
        corrections = dict()

        for criterion_name, option_name in staff_selected.iteritems():
            missing_option = criterion_name not in options_selected
            incorrect_option = options_selected[criterion_name] != option_name

            if missing_option or incorrect_option:
                corrections[criterion_name] = option_name

        return corrections
