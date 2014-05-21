"""
Database models for AI assessment.
"""
from uuid import uuid4
import json
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.utils.timezone import now
from django_extensions.db.fields import UUIDField
from .base import Rubric, Criterion
from .training import TrainingExample


class IncompleteClassifierSet(Exception):
    """
    The classifier set is missing a classifier for a criterion in the rubric.
    """
    def __init__(self, expected_criteria, actual_criteria):
        """
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

    # The rubric associated with this set of classifiers
    # We should have one classifier for each of the criteria in the rubric.
    rubric = models.ForeignKey(Rubric, related_name="+")

    # Timestamp for when the classifier set was created.
    # This allows us to find the most recently trained set of classifiers.
    created_at = models.DateTimeField(default=now, db_index=True)

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
        classifier_set = cls.objects.create(rubric=rubric)

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
                criterion=criterion,
                algorithm_id=algorithm_id
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

    # The ID of the algorithm that was used to train this classifier.
    algorithm_id = models.CharField(max_length=128, db_index=True)

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


class AITrainingWorkflow(models.Model):
    """
    Used to track all training tasks.

    Training tasks take as input an algorithm ID and a set of training examples
    (which are associated with a rubric).
    On successful completion, training tasks output a set of trained classifiers.

    """

    class Meta:
        app_label = "assessment"

    # Unique identifier used to track this workflow
    uuid = UUIDField(version=1, db_index=True)

    # The ID of the algorithm used to train the classifiers
    # This is a parameter passed to and interpreted by the workers.
    # Django settings allow the users to map algorithm ID strings
    # to the Python code they should use to perform the training.
    algorithm_id = models.CharField(max_length=128, db_index=True)

    # The training examples (essays + scores) used to train the classifiers.
    # This is a many-to-many field because
    # (a) we need multiple training examples to train a classifier, and
    # (b) we may want to re-use training examples
    # (for example, if a training task is executed by Celery workers multiple times)
    training_examples = models.ManyToManyField(TrainingExample, related_name="+")

    # The set of trained classifiers.
    # Until the task completes successfully, this will be set to null.
    classifier_set = models.ForeignKey(
        AIClassifierSet, related_name='training_workflow',
        null=True, default=None
    )

    # Timestamps
    # The task is *scheduled* as soon as a client asks the API to
    # train classifiers.
    # The task is *completed* when a worker has successfully created a
    # classifier set based on the training examples.
    scheduled_at = models.DateTimeField(default=now, db_index=True)
    completed_at = models.DateTimeField(null=True, db_index=True)

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

    @property
    def is_complete(self):
        """
        Check whether the workflow is complete (classifiers have been trained).

        Returns:
            bool

        """
        return self.completed_at is not None

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
        self.completed_at = now()
        self.save()
