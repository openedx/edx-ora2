"""
Database models for AI assessment.
"""
from uuid import uuid4
import json
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.utils.timezone import now
from django_extensions.db.fields import UUIDField
from submissions import api as sub_api
from openassessment.assessment.serializers import rubric_from_dict
from .base import Rubric, Criterion, Assessment, AssessmentPart
from .training import TrainingExample


AI_ASSESSMENT_TYPE = "AI"


class IncompleteClassifierSet(Exception):
    """
    The classifier set is missing a classifier for a criterion in the rubric.
    """
    def __init__(self, expected_criteria, actual_criteria):
        """
        Construct an error message that explains which criteria were missing.

        Args:
            expected_criteria (iterable of unicode): The criteria in the rubric.
            actual_criteria (iterable of unicode): The criteria specified by the classifier set.

        """
        missing_criteria = set(expected_criteria) - set(actual_criteria)
        msg = (
            u"Missing classifiers for the following "
            u"criteria: {missing}"
        ).format(missing=missing_criteria)
        super(IncompleteClassifierSet, self).__init__(msg)


class ClassifierUploadError(Exception):
    """
    An error occurred while uploading classifier data.
    """
    pass


class ClassifierSerializeError(Exception):
    """
    An error occurred while serializing classifier data.
    """
    pass


class NoTrainingExamples(Exception):
    """
    No training examples were provided to the workflow.
    """
    def __init__(self, workflow_uuid=None):
        msg = u"No training examples were provided"
        if workflow_uuid is not None:
            msg = u"{msg} to the training workflow with UUID {uuid}".format(
                msg=msg, uuid=workflow_uuid
            )
        super(NoTrainingExamples, self).__init__(msg)


class AIClassifierSet(models.Model):
    """
    A set of trained classifiers (immutable).
    """

    class Meta:
        app_label = "assessment"
        ordering = ['-created_at']

    # The rubric associated with this set of classifiers
    # We should have one classifier for each of the criteria in the rubric.
    rubric = models.ForeignKey(Rubric, related_name="+")

    # Timestamp for when the classifier set was created.
    # This allows us to find the most recently trained set of classifiers.
    created_at = models.DateTimeField(default=now, db_index=True)

    # The ID of the algorithm that was used to train classifiers in this set.
    algorithm_id = models.CharField(max_length=128, db_index=True)

    @classmethod
    @transaction.commit_on_success
    def create_classifier_set(cls, classifiers_dict, rubric, algorithm_id):
        """
        Create a set of classifiers.

        Args:
            classifiers_dict (dict): Mapping of criterion names to
                JSON-serializable classifiers.
            rubric (Rubric): The rubric model.
            algorithm_id (unicode): The ID of the algorithm used to train the classifiers.

        Returns:
            AIClassifierSet

        Raises:
            ClassifierSerializeError
            ClassifierUploadError
            DatabaseError

        """
        # Create the classifier set
        classifier_set = cls.objects.create(rubric=rubric, algorithm_id=algorithm_id)

        # Retrieve the criteria for this rubric,
        # then organize them by criterion name
        criteria = {
            criterion.name: criterion
            for criterion in Criterion.objects.filter(rubric=rubric)
        }

        # Check that we have classifiers for all criteria in the rubric
        if set(criteria.keys()) != set(classifiers_dict.keys()):
            raise IncompleteClassifierSet(criteria.keys(), classifiers_dict.keys())

        # Create classifiers for each criterion
        for criterion_name, classifier_data in classifiers_dict.iteritems():
            criterion = criteria.get(criterion_name)
            classifier = AIClassifier.objects.create(
                classifier_set=classifier_set,
                criterion=criterion
            )

            # Serialize the classifier data and upload
            try:
                contents = ContentFile(json.dumps(classifier_data))
            except (TypeError, ValueError, UnicodeDecodeError) as ex:
                msg = (
                    u"Could not serialize classifier data as JSON: {ex}"
                ).format(ex=ex)
                raise ClassifierSerializeError(msg)

            filename = uuid4().hex
            try:
                classifier.classifier_data.save(filename, contents)
            except Exception as ex:
                msg = (
                    u"Could not upload classifier data to {filename}: {ex}"
                ).format(filename=filename, ex=ex)
                raise ClassifierUploadError(msg)

        return classifier_set

    @property
    def classifiers_dict(self):
        """
        Return all classifiers in this classifier set in a dictionary
        that maps criteria names to classifier data.

        Returns:
            dict: keys are criteria names, values are JSON-serializable classifier data
            If there are no classifiers in the set, returns None

        """
        classifiers = list(self.classifiers.all())  # pylint: disable=E1101
        if len(classifiers) == 0:
            return None
        else:
            return {
                classifier.criterion.name: classifier.download_classifier_data()
                for classifier in classifiers
            }


class AIClassifier(models.Model):
    """
    A trained classifier (immutable).
    """

    class Meta:
        app_label = "assessment"

    # Directory in which classifiers will be stored
    # For instance, if we're using the default file system storage backend
    # for local development, this will be a subdirectory.
    # If using an S3 storage backend, this will be a subdirectory in
    # an AWS S3 bucket.
    AI_CLASSIFIER_STORAGE = "ora2_ai_classifiers"

    # The set of classifiers this classifier belongs to
    classifier_set = models.ForeignKey(AIClassifierSet, related_name="classifiers")

    # The criterion (in the rubric) that this classifier evaluates.
    criterion = models.ForeignKey(Criterion, related_name="+")

    # The serialized classifier
    # Because this may be large, we store it using a Django `FileField`,
    # which allows us to plug in different storage backends (such as S3)
    classifier_data = models.FileField(upload_to=AI_CLASSIFIER_STORAGE)

    def download_classifier_data(self):
        """
        Download and deserialize the classifier data.

        Returns:
            JSON-serializable

        Raises:
            ValueError
            IOError

        """
        return json.loads(self.classifier_data.read())  # pylint:disable=E1101


class AIWorkflow(models.Model):
    """
    Abstract base class for AI workflow database models.
    """
    class Meta:
        app_label = "assessment"
        abstract = True

    # Unique identifier used to track this workflow
    uuid = UUIDField(version=1, db_index=True)

    # Timestamps
    # The task is *scheduled* as soon as a client asks the API to
    # train classifiers.
    # The task is *completed* when a worker has successfully created a
    # classifier set based on the training examples.
    scheduled_at = models.DateTimeField(default=now, db_index=True)
    completed_at = models.DateTimeField(null=True, db_index=True)

    # The ID of the algorithm used to train the classifiers
    # This is a parameter passed to and interpreted by the workers.
    # Django settings allow the users to map algorithm ID strings
    # to the Python code they should use to perform the training.
    algorithm_id = models.CharField(max_length=128, db_index=True)

    # The set of trained classifiers.
    # In the training task, this field will be set when the task completes successfully.
    # In the grading task, this may be set to null if no classifiers are available
    # when the student submits an essay for grading.
    classifier_set = models.ForeignKey(
        AIClassifierSet, related_name='+',
        null=True, default=None
    )

    @property
    def is_complete(self):
        """
        Check whether the workflow is complete.

        Returns:
            bool

        """
        return self.completed_at is not None

    def mark_complete_and_save(self):
        """
        Mark the workflow as complete.

        Returns:
            None

        """
        self.completed_at = now()
        self.save()


class AITrainingWorkflow(AIWorkflow):
    """
    Used to track AI training tasks.

    Training tasks take as input an algorithm ID and a set of training examples
    (which are associated with a rubric).
    On successful completion, training tasks output a set of trained classifiers.

    """
    class Meta:
        app_label = "assessment"

    # The training examples (essays + scores) used to train the classifiers.
    # This is a many-to-many field because
    # (a) we need multiple training examples to train a classifier, and
    # (b) we may want to re-use training examples
    # (for example, if a training task is executed by Celery workers multiple times)
    training_examples = models.ManyToManyField(TrainingExample, related_name="+")

    @classmethod
    @transaction.commit_on_success
    def start_workflow(cls, examples, algorithm_id):
        """
        Start a workflow to track a training task.

        Args:
            examples (list of TrainingExample): The training examples used to create the classifiers.
            algorithm_id (unicode): The ID of the algorithm to use for training.

        Returns:
            AITrainingWorkflow

        Raises:
            NoTrainingExamples

        """
        if len(examples) == 0:
            raise NoTrainingExamples()

        workflow = AITrainingWorkflow.objects.create(algorithm_id=algorithm_id)
        workflow.training_examples.add(*examples)
        workflow.save()
        return workflow

    @property
    def rubric(self):
        """
        Return the rubric associated with this classifier set.

        Returns:
            Rubric or None (if no training examples are available)

        Raises:
            NoTrainingExamples

        """
        # We assume that all the training examples we have been provided are using
        # the same rubric (this is enforced by the API call that deserializes
        # the training examples).
        first_example = list(self.training_examples.all()[:1])  # pylint: disable=E1101
        if first_example:
            return first_example[0].rubric
        else:
            raise NoTrainingExamples(workflow_uuid=self.uuid)

    def complete(self, classifier_set):
        """
        Add a classifier set to the workflow and mark it complete.

        Args:
            classifier_set (dict): Mapping of criteria names to serialized classifiers.

        Returns:
            None

        Raises:
            NoTrainingExamples
            IncompleteClassifierSet
            ClassifierSerializeError
            ClassifierUploadError
            DatabaseError
        """
        self.classifier_set = AIClassifierSet.create_classifier_set(
            classifier_set, self.rubric, self.algorithm_id
        )
        self.mark_complete_and_save()


class AIGradingWorkflow(AIWorkflow):
    """
    Used to track AI grading tasks.

    Grading tasks take as input an essay submission
    and a set of classifiers; the tasks select options
    for each criterion in the rubric.

    """
    class Meta:
        app_label = "assessment"

    # The UUID of the submission being graded
    submission_uuid = models.CharField(max_length=128, db_index=True)

    # The text of the essay submission to grade
    # We duplicate this here to avoid having to repeatedly look up
    # the submission.  Since submissions are immutable, this is safe.
    essay_text = models.TextField(blank=True)

    # The rubric used to evaluate the submission.
    # We store this so we can look for classifiers for the same rubric
    # if none are available when the workflow is created.
    rubric = models.ForeignKey(Rubric, related_name="+")

    # The assessment produced by the AI grading algorithm
    # Until the task completes successfully, this will be set to null
    assessment = models.ForeignKey(
        Assessment, related_name="+", null=True, default=None
    )

    # Identifier information associated with the student's submission
    # Useful for finding workflows for a particular course/item/student
    # Since submissions are immutable, and since the workflow is
    # associated with one submission, it's safe to duplicate
    # this information here from the submissions models.
    student_id = models.CharField(max_length=40, db_index=True)
    item_id = models.CharField(max_length=128, db_index=True)
    course_id = models.CharField(max_length=40, db_index=True)

    @classmethod
    @transaction.commit_on_success
    def start_workflow(cls, submission_uuid, rubric_dict, algorithm_id):
        """
        Start a grading workflow.

        Args:
            submission_uuid (str): The UUID of the submission to grade.
            rubric_dict (dict): The serialized rubric model.
            algorithm_id (unicode): The ID of the algorithm to use for grading.

        Returns:
            AIGradingWorkflow

        Raises:
            SubmissionNotFoundError
            SubmissionRequestError
            SubmissionInternalError
            InvalidRubric
            DatabaseError

        """
        # Retrieve info about the submission
        submission = sub_api.get_submission_and_student(submission_uuid)

        # Get or create the rubric
        rubric = rubric_from_dict(rubric_dict)

        # Retrieve the submission text
        # Submissions are arbitrary JSON-blobs, which *should*
        # contain a single key, "answer", containing the essay
        # submission text.  If not, though, assume we've been
        # given the essay text directly (convenient for testing).
        if isinstance(submission, dict):
            essay_text = submission.get('answer')
        else:
            essay_text = unicode(submission)

        # Create the workflow
        return cls.objects.create(
            submission_uuid=submission_uuid,
            essay_text=essay_text,
            algorithm_id=algorithm_id,
            student_id=submission['student_item']['student_id'],
            item_id=submission['student_item']['item_id'],
            course_id=submission['student_item']['course_id'],
            rubric=rubric
        )

    @transaction.commit_on_success
    def complete(self, criterion_scores):
        """
        Create an assessment with scores from the AI classifiers
        and mark the workflow complete.

        Args:
            criterion_scores (dict): Dictionary mapping criteria names to integer scores.

        Raises:
            DatabaseError

        """
        assessment = Assessment.objects.create(
            submission_uuid=self.submission_uuid,
            rubric=self.rubric,
            scorer_id=self.algorithm_id,
            score_type=AI_ASSESSMENT_TYPE
        )

        option_ids = self.rubric.options_ids_for_points(criterion_scores)
        AssessmentPart.add_to_assessment(assessment, option_ids)

        self.assessment = assessment
        self.mark_complete_and_save()
