# coding=utf-8
"""
Tests for AI worker tasks.
"""
from contextlib import contextmanager
import mock
from django.test.utils import override_settings
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.worker.training import train_classifiers, InvalidExample
from openassessment.assessment.api import ai_worker as ai_worker_api
from openassessment.assessment.models import AITrainingWorkflow
from openassessment.assessment.worker.algorithm import (
    AIAlgorithm, UnknownAlgorithm, AlgorithmLoadError, TrainingError
)
from openassessment.assessment.serializers import deserialize_training_examples
from openassessment.assessment.errors import AITrainingRequestError
from openassessment.assessment.test.constants import EXAMPLES, RUBRIC


class StubAIAlgorithm(AIAlgorithm):
    """
    Stub implementation of a supervised ML algorithm.
    """
    def train_classifier(self, examples):
        return {}

    def score(self, text, classifier):
        raise NotImplementedError


class ErrorStubAIAlgorithm(AIAlgorithm):
    """
    Stub implementation that raises an exception during training.
    """
    def train_classifier(self, examples):
        raise TrainingError("Test error!")

    def score(self, text, classifier):
        raise NotImplementedError


class AITrainingTaskTest(CacheResetTest):
    """
    Tests for the training task executed asynchronously by Celery workers.
    """

    ALGORITHM_ID = u"test-stub"
    ERROR_STUB_ALGORITHM_ID = u"error-stub"
    UNDEFINED_CLASS_ALGORITHM_ID = u"undefined_class"
    UNDEFINED_MODULE_ALGORITHM_ID = u"undefined_module"
    AI_ALGORITHMS = {
        ALGORITHM_ID: '{module}.StubAIAlgorithm'.format(module=__name__),
        ERROR_STUB_ALGORITHM_ID: '{module}.ErrorStubAIAlgorithm'.format(module=__name__),
        UNDEFINED_CLASS_ALGORITHM_ID: '{module}.NotDefinedAIAlgorithm'.format(module=__name__),
        UNDEFINED_MODULE_ALGORITHM_ID: 'openassessment.not.valid.NotDefinedAIAlgorithm'
    }

    def setUp(self):
        """
        Create a training workflow in the database.
        """
        examples = deserialize_training_examples(EXAMPLES, RUBRIC)
        workflow = AITrainingWorkflow.start_workflow(examples, self.ALGORITHM_ID)
        self.workflow_uuid = workflow.uuid

    def test_unknown_algorithm(self):
        # Since we haven't overridden settings to configure the algorithms,
        # the worker will not recognize the workflow's algorithm ID.
        with self._assert_retry(train_classifiers, UnknownAlgorithm):
            train_classifiers(self.workflow_uuid)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_unable_to_load_algorithm_class(self):
        # The algorithm is defined in the settings, but the class does not exist.
        self._set_algorithm_id(self.UNDEFINED_CLASS_ALGORITHM_ID)
        with self._assert_retry(train_classifiers, AlgorithmLoadError):
            train_classifiers(self.workflow_uuid)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_unable_to_find_algorithm_module(self):
        # The algorithm is defined in the settings, but the module can't be loaded
        self._set_algorithm_id(self.UNDEFINED_MODULE_ALGORITHM_ID)
        with self._assert_retry(train_classifiers, AlgorithmLoadError):
            train_classifiers(self.workflow_uuid)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @mock.patch('openassessment.assessment.worker.training.ai_worker_api.get_training_task_params')
    def test_get_training_task_params_api_error(self, mock_call):
        mock_call.side_effect = AITrainingRequestError("Test error!")
        with self._assert_retry(train_classifiers, AITrainingRequestError):
            train_classifiers(self.workflow_uuid)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_invalid_training_example_error(self):
        def _mutation(examples):    # pylint: disable=C0111
            del examples[0]['scores'][u"ﻭɼค๓๓คɼ"]
        self._assert_mutated_examples(_mutation)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_training_example_missing_key(self):
        def _mutation(examples):    # pylint: disable=C0111
            del examples[0]['scores']
        self._assert_mutated_examples(_mutation)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_training_example_non_numeric_score(self):
        def _mutation(examples):    # pylint: disable=C0111
            examples[0]['scores'][u"ﻭɼค๓๓คɼ"] = "not an integer"
        self._assert_mutated_examples(_mutation)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_training_algorithm_error(self):
        # Use a stub algorithm implementation that raises an exception during training
        self._set_algorithm_id(self.ERROR_STUB_ALGORITHM_ID)
        with self._assert_retry(train_classifiers, TrainingError):
            train_classifiers(self.workflow_uuid)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @mock.patch('openassessment.assessment.worker.training.ai_worker_api.create_classifiers')
    def test_create_classifiers_api_error(self, mock_call):
        mock_call.side_effect = AITrainingRequestError("Test error!")
        with self._assert_retry(train_classifiers, AITrainingRequestError):
            train_classifiers(self.workflow_uuid)

    def _set_algorithm_id(self, algorithm_id):
        """
        Override the default algorithm ID for the training workflow.

        Args:
            algorithm_id (unicode): The new algorithm ID

        Returns:
            None

        """
        workflow = AITrainingWorkflow.objects.get(uuid=self.workflow_uuid)
        workflow.algorithm_id = algorithm_id
        workflow.save()

    def _assert_mutated_examples(self, mutate_func):
        """
        Mutate the training examples returned by the API,
        then check that we get the expected error.

        This *may* be a little paranoid :)

        Args:
            mutate_func (callable): Function that accepts a single argument,
                the list of example dictionaries.

        Raises:
            AssertionError

        """
        params = ai_worker_api.get_training_task_params(self.workflow_uuid)
        mutate_func(params['training_examples'])

        call_signature = 'openassessment.assessment.worker.training.ai_worker_api.get_training_task_params'
        with mock.patch(call_signature) as mock_call:
            mock_call.return_value = params
            with self._assert_retry(train_classifiers, InvalidExample):
                train_classifiers(self.workflow_uuid)

    @contextmanager
    def _assert_retry(self, task, final_exception):
        """
        Context manager that asserts that the training task was retried.

        Args:
            task (celery.app.task.Task): The Celery task object.
            final_exception (Exception): The error thrown after retrying.

        Raises:
            AssertionError

        """
        original_retry = task.retry
        task.retry = mock.MagicMock()
        task.retry.side_effect = lambda: original_retry(task)
        try:
            with self.assertRaises(final_exception):
                yield
            task.retry.assert_called_once()
        finally:
            task.retry = original_retry
