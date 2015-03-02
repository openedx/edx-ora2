"""
Database models for AI assessment.
"""
from uuid import uuid4
import json
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.cache import cache, get_cache
from django.db import models, transaction, DatabaseError
from django.utils.timezone import now
from django_extensions.db.fields import UUIDField
from dogapi import dog_stats_api
from submissions import api as sub_api
from .base import Rubric, Criterion, Assessment, AssessmentPart
from .training import TrainingExample


AI_ASSESSMENT_TYPE = "AI"

logger = logging.getLogger(__name__)


# Use an in-memory cache to hold classifier data, but allow settings to override this.
# The classifier data will generally be larger than memcached's default max size
CLASSIFIERS_CACHE_IN_MEM = getattr(
    settings, 'ORA2_CLASSIFIERS_CACHE_IN_MEM',
    get_cache(
        'django.core.cache.backends.locmem.LocMemCache',
        LOCATION='openassessment.ai.classifiers_dict'
    )
)

CLASSIFIERS_CACHE_IN_FILE = getattr(
    settings, 'ORA2_CLASSIFIERS_CACHE_IN_FILE',
    get_cache(
        'django.core.cache.backends.filebased.FileBasedCache',
        LOCATION='/tmp/ora2_classifier_cache'
    )
)


def essay_text_from_submission(submission):
    """
    Retrieve the submission text.

    Submissions are arbitrary JSON-blobs, which *should*
    contain a single key, "answer", containing the essay
    submission text.
    If not, though, assume we've been given the essay text
    directly (convenient for testing).
    """
    if isinstance(submission, dict):
        if 'answer' in submission:
            # Format used for answer in examples.
            if isinstance(submission['answer'], unicode):
                return submission['answer']
            # Initially there was one prompt and submission had the structure
            # {'answer': {'text': 'The text.'}}
            elif 'text' in submission['answer']:
                essay_text = submission['answer']['text']
            # When multiple prompts were introduced the structure of submission become:
            # {'answer': {'parts': [{'text': 'The text part 1.'}, {'text': 'The text part 2.'}]}}
            # We concatenate these parts and let AI grader evaluate the total text.
            else:
                essay_text = u'\n'.join([part['text'] for part in submission['answer']['parts']])
    else:
        essay_text = unicode(submission)
    return essay_text


class IncompleteClassifierSet(Exception):
    """
    The classifier set is missing a classifier for a criterion in the rubric.
    """
    def __init__(self, missing_criteria):
        """
        Construct an error message that explains which criteria were missing.

        Args:
            missing_criteria (list): The list of criteria names that were missing.

        """
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
        ordering = ['-created_at', '-id']

    # The rubric associated with this set of classifiers
    # We should have one classifier for each of the criteria in the rubric.
    rubric = models.ForeignKey(Rubric, related_name="+")

    # Timestamp for when the classifier set was created.
    # This allows us to find the most recently trained set of classifiers.
    created_at = models.DateTimeField(default=now, db_index=True)

    # The ID of the algorithm that was used to train classifiers in this set.
    algorithm_id = models.CharField(max_length=128, db_index=True)

    # Course Entity and Item Discriminator
    # Though these items are duplicated in the database tables for the AITrainingWorkflow,
    # this is okay because it will drastically speed up the operation of assigning classifiers
    # to AIGradingWorkflows
    course_id = models.CharField(max_length=40, db_index=True)
    item_id = models.CharField(max_length=128, db_index=True)

    @classmethod
    @transaction.commit_on_success
    def create_classifier_set(cls, classifiers_dict, rubric, algorithm_id, course_id, item_id):
        """
        Create a set of classifiers.

        Args:
            classifiers_dict (dict): Mapping of criterion names to
                JSON-serializable classifiers.
            rubric (Rubric): The rubric model.
            algorithm_id (unicode): The ID of the algorithm used to train the classifiers.
            course_id (unicode): The ID of the course that the classifier is going to be grading
            item_id (unicode): The item within the course that the classifier is trained to grade.

        Returns:
            AIClassifierSet

        Raises:
            ClassifierSerializeError
            ClassifierUploadError
            InvalidRubricSelection
            DatabaseError

        """
        # Create the classifier set
        classifier_set = cls.objects.create(
            rubric=rubric, algorithm_id=algorithm_id, item_id=item_id, course_id=course_id
        )

        # Retrieve the criteria for this rubric,
        # then organize them by criterion name
        try:
            rubric_index = rubric.index
        except DatabaseError as ex:
            msg = (
                u"An unexpected error occurred while retrieving rubric criteria with the"
                u"rubric hash {rh} and algorithm_id {aid}: {ex}"
            ).format(rh=rubric.content_hash, aid=algorithm_id, ex=ex)
            logger.exception(msg)
            raise

        # Check that we have classifiers for all criteria in the rubric
        # Ignore criteria that have no options: since these have only written feedback,
        # we can't assign them a score.
        all_criteria = set(classifiers_dict.keys())
        all_criteria |= set(
            criterion.name for criterion in 
            rubric_index.find_criteria_without_options()
        )
        missing_criteria = rubric_index.find_missing_criteria(all_criteria)
        if missing_criteria:
            raise IncompleteClassifierSet(missing_criteria)

        # Create classifiers for each criterion
        for criterion_name, classifier_data in classifiers_dict.iteritems():
            classifier = AIClassifier.objects.create(
                classifier_set=classifier_set,
                criterion=rubric_index.find_criterion(criterion_name)
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
                full_filename = upload_to_path(classifier, filename)
                msg = (
                    u"Could not upload classifier data to {filename}: {ex}"
                ).format(filename=full_filename, ex=ex)
                raise ClassifierUploadError(msg)

        return classifier_set

    @classmethod
    def most_recent_classifier_set(cls, rubric, algorithm_id, course_id, item_id):
        """
        Finds the most relevant classifier set based on the following line of succession:

            1 -- Classifier sets with the same COURSE, ITEM, RUBRIC *content* hash, and ALGORITHM
                - Newest first.  If none exist...
            2 -- Classifier sets with the same COURSE, ITEM, and RUBRIC *structure* hash, and ALGORITHM.
                - Newest first.  If none exist...
            3 -- The newest classifier set with the same RUBRIC and ALGORITHM
                - Newest first.  If none exist...
            4 -- Do no assignment and return False

        Case #1 is ideal: we get a classifier set trained for the rubric as currently defined.

        Case #2 handles when a course author makes a cosmetic change to a rubric after training.
            We don't want to stop grading students because an author fixed a typo!

        Case #3 handles problems that are duplicated, such as the default problem prompt.
            If we've already trained classifiers for the identical rubric somewhere else,
            then the author can use them to test out the feature immediately.

        Case #4: Someone will need to schedule training; however, we will still accept
            student submissions and grade them once training completes.

        Args:
            rubric (Rubric): The rubric associated with the classifier set.
            algorithm_id (unicode): The algorithm used to create the classifier set.
            course_id (unicode): The course identifier for the current problem.
            item_id (unicode): The item identifier for the current problem.

        Returns:
            ClassifierSet or None

        Raises:
            DatabaseError

        """
        # List of the parameters we will search for, in order of decreasing priority
        search_parameters = [
            # Case #1: same course / item / rubric (exact) / algorithm
            {
                'rubric__content_hash': rubric.content_hash,
                'algorithm_id': algorithm_id,
                'course_id': course_id,
                'item_id': item_id
            },

            # Case #2: same course / item / rubric (structure only) / algorithm
            {
                'rubric__structure_hash': rubric.structure_hash,  # pylint: disable=E1101
                'algorithm_id': algorithm_id,
                'course_id': course_id,
                'item_id': item_id
            },

            # Case #3: same rubric (exact) / algorithm
            {
                'rubric__content_hash': rubric.content_hash,
                'algorithm_id': algorithm_id
            }
        ]

        # Perform each query, starting with the highest priority
        for params in search_parameters:

            # Retrieve the most recent classifier set that matches our query
            # (rely on implicit ordering in the model definition)
            classifier_set_candidates = cls.objects.filter(**params)[:1]

            # If we find a classifier set,
            # then associate the most recent classifiers with it and return true
            if len(classifier_set_candidates) > 0:
                return classifier_set_candidates[0]

        # If we get to this point, no classifiers exist with this rubric and algorithm.
        return None

    @property
    def classifier_data_by_criterion(self):
        """
        Return info for all classifiers in this classifier set in a dictionary
        that maps criteria names to classifier data.

        Returns:
            dict: keys are criteria names, values are JSON-serializable classifier data

        Raises:
            ValueError
            IOError
            httplib.HTTPException

        """
        # First check the in-memory cache
        # We use an in-memory cache because the classifier data will most often
        # be several megabytes, which exceeds the default memcached size limit.
        # If we find it, we can avoid calls to the database, S3, and json.
        cache_key = self._cache_key("classifier_data_by_criterion")
        classifiers_dict = CLASSIFIERS_CACHE_IN_MEM.get(cache_key)

        # If we can't find the classifier in-memory, check the filesystem cache
        # We can't always rely on the in-memory cache because worker processes
        # terminate when max retries are exceeded.
        if classifiers_dict is None:
            msg = (
                u"Could not find classifiers dict in the in-memory "
                u"cache for key {key}.  Falling back to the file-based cache."
            ).format(key=cache_key)
            logger.info(msg)
            classifiers_dict = CLASSIFIERS_CACHE_IN_FILE.get(cache_key)
        else:
            msg = (
                u"Found classifiers dict in the in-memory cache "
                u"(cache key was {key})"
            ).format(key=cache_key)
            logger.info(msg)

        # If we can't find the classifiers dict in the cache,
        # we need to look up the classifiers in the database,
        # then download the classifier data.
        if classifiers_dict is None:
            classifiers_dict = {
                classifier.criterion.name: classifier.download_classifier_data()
                for classifier in self.classifiers.select_related().all()   # pylint: disable=E1101
            }
            CLASSIFIERS_CACHE_IN_MEM.set(cache_key, classifiers_dict)
            CLASSIFIERS_CACHE_IN_FILE.set(cache_key, classifiers_dict)
            msg = (
                u"Could not find classifiers dict in either the in-memory "
                u"or file-based cache.  Downloaded the data from S3 and cached "
                u"it using key {key}"
            ).format(key=cache_key)
            logger.info(msg)

        return classifiers_dict

    @property
    def valid_scores_by_criterion(self):
        """
        Return the valid scores for each classifier in this classifier set.

        Returns:
            dict: maps rubric criterion names to lists of valid scores.

        """
        cache_key = self._cache_key("valid_scores_by_criterion")
        valid_scores_by_criterion = cache.get(cache_key)
        if valid_scores_by_criterion is None:
            valid_scores_by_criterion = {
                classifier.criterion.name: classifier.valid_scores
                for classifier in self.classifiers.select_related().all()  # pylint: disable=E1101
            }
            cache.set(cache_key, valid_scores_by_criterion)
        return valid_scores_by_criterion

    def _cache_key(self, data_name):
        """
        Return a cache key for this classifier set.

        Args:
            data_name (unicode): Name for the data associated with this key.

        Returns:
            unicode

        """
        return u"openassessment.assessment.ai.classifier_set.{pk}.{data_name}".format(
            pk=self.pk, data_name=data_name
        )


# Directory in which classifiers will be stored
# For instance, if we're using the default file system storage backend
# for local development, this will be a subdirectory.
# If using an S3 storage backend, this will be a subdirectory in
# an AWS S3 bucket.
AI_CLASSIFIER_STORAGE = "ora2_ai_classifiers"

def upload_to_path(instance, filename):    # pylint:disable=W0613
    """
    Calculate the file path where classifiers should be uploaded.
    Optionally prepends the path with a prefix (determined by Django settings).
    This allows us to put classifiers from different environments
    (stage / prod) in different directories within the same S3 bucket.

    Args:
        instance (AIClassifier): Not used.
        filename (unicode): The filename provided when saving the file.

    Returns:
        unicode

    """
    prefix = getattr(settings, 'ORA2_FILE_PREFIX', None)
    if prefix is not None:
        return u"{prefix}/{root}/{filename}".format(
            prefix=prefix,
            root=AI_CLASSIFIER_STORAGE,
            filename=filename
        )
    else:
        return u"{root}/{filename}".format(
            root=AI_CLASSIFIER_STORAGE,
            filename=filename
        )


class AIClassifier(models.Model):
    """
    A trained classifier (immutable).
    """

    class Meta:
        app_label = "assessment"

    # The set of classifiers this classifier belongs to
    classifier_set = models.ForeignKey(AIClassifierSet, related_name="classifiers")

    # The criterion (in the rubric) that this classifier evaluates.
    criterion = models.ForeignKey(Criterion, related_name="+")

    # The serialized classifier
    # Because this may be large, we store it using a Django `FileField`,
    # which allows us to plug in different storage backends (such as S3)
    classifier_data = models.FileField(upload_to=upload_to_path)

    def download_classifier_data(self):
        """
        Download and deserialize the classifier data.

        Returns:
            JSON-serializable

        Raises:
            ValueError
            IOError
            httplib.HTTPException

        """
        return json.loads(self.classifier_data.read())  # pylint:disable=E1101

    @property
    def valid_scores(self):
        """
        Return a list of valid scores for the rubric criterion associated
        with this classifier.

        Returns:
            list of integer scores, in ascending order.

        """
        return sorted([option.points for option in self.criterion.options.all()])


class AIWorkflow(models.Model):
    """
    Abstract base class for AI workflow database models.
    """
    class Meta:
        app_label = "assessment"
        abstract = True

    # Unique identifier used to track this workflow
    uuid = UUIDField(version=1, db_index=True, unique=True)

    # Course Entity and Item Discriminator
    # Though these items are duplicated in the database tables for the submissions app,
    # and every workflow has a reference to a submission entry, this is okay because
    # submissions are immutable.
    course_id = models.CharField(max_length=40, db_index=True)
    item_id = models.CharField(max_length=128, db_index=True)

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
        self._log_complete_workflow()

    @classmethod
    def get_incomplete_workflows(cls, course_id, item_id):
        """
        Gets all incomplete grading workflows for a given course and item.

        Args:
            course_id (unicode): Uniquely identifies the course
            item_id (unicode): The discriminator for the item we are looking for

        Yields:
            All incomplete workflows for this item, as a delayed "stream"

        Raises:
            DatabaseError
            cls.DoesNotExist
        """

        # Finds all of the uuid's for workflows contained within the query
        grade_workflow_uuids = [
            wflow['uuid'] for wflow in cls.objects.filter(
                course_id=course_id, item_id=item_id, completed_at__isnull=True
            ).values('uuid')
        ]

        # Continues to generate output until all workflows in the queryset have been output
        for workflow_uuid in grade_workflow_uuids:

            # Returns the grading workflow associated with the uuid stored in the initial query
            workflow = cls.objects.get(uuid=workflow_uuid)
            yield workflow

    @classmethod
    def is_workflow_complete(cls, workflow_uuid):
        """
        Check whether the workflow with a given UUID has been marked complete.

        Args:
            workflow_uuid (str): The UUID of the workflow to check.

        Returns:
            bool

        Raises:
            DatabaseError
            cls.DoesNotExist

        """
        workflow = cls.objects.get(uuid=workflow_uuid)
        return workflow.is_complete

    def _log_start_workflow(self):
        """
        A logging operation called at the beginning of an AI Workflows life.
        Increments the number of tasks of that kind.
        """

        # Identifies whether the type of task for reporting
        class_name = self.__class__.__name__
        data_path = 'openassessment.assessment.ai_task.' + class_name

        # Sets identity tags which allow sorting by course and item
        tags = [
            u"course_id:{course_id}".format(course_id=self.course_id),
            u"item_id:{item_id}".format(item_id=self.item_id),
        ]

        logger.info(u"{class_name} with uuid {uuid} was started.".format(class_name=class_name, uuid=self.uuid))

        dog_stats_api.increment(data_path + '.scheduled_count', tags=tags)

    def _log_complete_workflow(self):
        """
        A logging operation called at the end of an AI Workflow's Life
        Reports the total time the task took.
        """

        # Identifies whether the type of task for reporting
        class_name = self.__class__.__name__
        data_path = 'openassessment.assessment.ai_task.' + class_name

        tags = [
            u"course_id:{course_id}".format(course_id=self.course_id),
            u"item_id:{item_id}".format(item_id=self.item_id),
        ]

        # Calculates the time taken to complete the task and reports it to datadog
        time_delta = self.completed_at - self.scheduled_at
        dog_stats_api.histogram(
            data_path + '.turnaround_time',
            time_delta.total_seconds(),
            tags=tags
        )

        dog_stats_api.increment(data_path + '.completed_count', tags=tags)

        logger.info(
            (
                u"{class_name} with uuid {uuid} completed its workflow successfully "
                u"in {seconds} seconds."
            ).format(class_name=class_name, uuid=self.uuid, seconds=time_delta.total_seconds())
        )


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
    def start_workflow(cls, examples, course_id, item_id, algorithm_id):
        """
        Start a workflow to track a training task.

        Args:
            examples (list of TrainingExample): The training examples used to create the classifiers.
            course_id (unicode): The ID for the course that the training workflow is associated with.
            item_id (unicode): The ID for the item that the training workflow is training to assess.
            algorithm_id (unicode): The ID of the algorithm to use for training.

        Returns:
            AITrainingWorkflow

        Raises:
            NoTrainingExamples

        """
        if len(examples) == 0:
            raise NoTrainingExamples()

        workflow = AITrainingWorkflow.objects.create(algorithm_id=algorithm_id, item_id=item_id, course_id=course_id)
        workflow.training_examples.add(*examples)
        workflow.save()
        workflow._log_start_workflow()
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
            InvalidRubricSelection
            DatabaseError
        """
        self.classifier_set = AIClassifierSet.create_classifier_set(
            classifier_set, self.rubric, self.algorithm_id, self.course_id, self.item_id
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

    def assign_most_recent_classifier_set(self):
        """
        Find the most recent classifier set and assign it to this workflow.

        Returns:
            (bool) indicates whether or not classifiers were able to be assigned to the AIGradingWorkflow

        Raises:
            DatabaseError
        """
        classifier_set = AIClassifierSet.most_recent_classifier_set(
            self.rubric, self.algorithm_id, self.course_id, self.item_id
        )
        if classifier_set is not None:
            self.classifier_set = classifier_set
            self.save()
        return classifier_set is not None

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
        from openassessment.assessment.serializers import rubric_from_dict
        rubric = rubric_from_dict(rubric_dict)

        # Create the workflow
        workflow = cls.objects.create(
            submission_uuid=submission_uuid,
            essay_text=essay_text_from_submission(submission),
            algorithm_id=algorithm_id,
            student_id=submission['student_item']['student_id'],
            item_id=submission['student_item']['item_id'],
            course_id=submission['student_item']['course_id'],
            rubric=rubric
        )

        # Retrieve and assign classifier set candidates
        workflow.assign_most_recent_classifier_set()

        workflow._log_start_workflow()

        return workflow

    @transaction.commit_on_success
    def complete(self, criterion_scores):
        """
        Create an assessment with scores from the AI classifiers
        and mark the workflow complete.

        Args:
            criterion_scores (dict): Dictionary mapping criteria names to integer scores.

        Raises:
            InvalidRubricSelection
            DatabaseError

        """
        self.assessment = Assessment.create(
            self.rubric, self.algorithm_id, self.submission_uuid, AI_ASSESSMENT_TYPE
        )
        AssessmentPart.create_from_option_points(self.assessment, criterion_scores)
        self.mark_complete_and_save()
