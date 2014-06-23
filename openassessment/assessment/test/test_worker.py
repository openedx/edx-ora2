# coding=utf-8
"""
Tests for AI worker tasks.
"""
from contextlib import contextmanager
import itertools
import mock
from django.test.utils import override_settings
from submissions import api as sub_api
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.worker.training import train_classifiers, InvalidExample
from openassessment.assessment.worker.grading import grade_essay
from openassessment.assessment.api import ai_worker as ai_worker_api
from openassessment.assessment.models import AITrainingWorkflow, AIGradingWorkflow, AIClassifierSet
from openassessment.assessment.worker.algorithm import (
    AIAlgorithm, UnknownAlgorithm, AlgorithmLoadError, TrainingError, ScoreError
)
from openassessment.assessment.serializers import (
    deserialize_training_examples, rubric_from_dict
)
from openassessment.assessment.errors import AITrainingRequestError, AIGradingInternalError
from openassessment.assessment.test.constants import (
    EXAMPLES, RUBRIC, STUDENT_ITEM, ANSWER
)


class StubAIAlgorithm(AIAlgorithm):
    """
    Stub implementation of a supervised ML algorithm.
    """
    def train_classifier(self, examples):
        return {}

    def score(self, text, classifier, cache):
        return 0


class ErrorStubAIAlgorithm(AIAlgorithm):
    """
    Stub implementation that raises an exception during training.
    """
    def train_classifier(self, examples):
        raise TrainingError("Test error!")

    def score(self, text, classifier, cache):
        raise ScoreError("Test error!")


class InvalidScoreAlgorithm(AIAlgorithm):
    """
    Stub implementation that returns a score that isn't in the rubric.
    """
    SCORE_CYCLE = itertools.cycle([-100, 0.7, 1.2, 100])

    def train_classifier(self, examples):
        return {}

    def score(self, text, classifier, cache):
        return self.SCORE_CYCLE.next()


ALGORITHM_ID = u"test-stub"
ERROR_STUB_ALGORITHM_ID = u"error-stub"
UNDEFINED_CLASS_ALGORITHM_ID = u"undefined_class"
UNDEFINED_MODULE_ALGORITHM_ID = u"undefined_module"
INVALID_SCORE_ALGORITHM_ID = u"invalid_score"
AI_ALGORITHMS = {
    ALGORITHM_ID: '{module}.StubAIAlgorithm'.format(module=__name__),
    ERROR_STUB_ALGORITHM_ID: '{module}.ErrorStubAIAlgorithm'.format(module=__name__),
    UNDEFINED_CLASS_ALGORITHM_ID: '{module}.NotDefinedAIAlgorithm'.format(module=__name__),
    UNDEFINED_MODULE_ALGORITHM_ID: 'openassessment.not.valid.NotDefinedAIAlgorithm',
    INVALID_SCORE_ALGORITHM_ID: '{module}.InvalidScoreAlgorithm'.format(module=__name__),
}


class CeleryTaskTest(CacheResetTest):
    """
    Test case for Celery tasks.
    """
    @contextmanager
    def assert_retry(self, task, final_exception):
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


class AITrainingTaskTest(CeleryTaskTest):
    """
    Tests for the training task executed asynchronously by Celery workers.
    """

    COURSE_ID = u"10923"
    ITEM_ID = u"12231"
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
        workflow = AITrainingWorkflow.start_workflow(examples, self.COURSE_ID, self.ITEM_ID, self.ALGORITHM_ID)
        self.workflow_uuid = workflow.uuid

    def test_unknown_algorithm(self):
        # Since we haven't overridden settings to configure the algorithms,
        # the worker will not recognize the workflow's algorithm ID.
        with self.assert_retry(train_classifiers, UnknownAlgorithm):
            train_classifiers(self.workflow_uuid)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_unable_to_load_algorithm_class(self):
        # The algorithm is defined in the settings, but the class does not exist.
        self._set_algorithm_id(UNDEFINED_CLASS_ALGORITHM_ID)
        with self.assert_retry(train_classifiers, AlgorithmLoadError):
            train_classifiers(self.workflow_uuid)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_unable_to_find_algorithm_module(self):
        # The algorithm is defined in the settings, but the module can't be loaded
        self._set_algorithm_id(UNDEFINED_MODULE_ALGORITHM_ID)
        with self.assert_retry(train_classifiers, AlgorithmLoadError):
            train_classifiers(self.workflow_uuid)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @mock.patch('openassessment.assessment.worker.training.ai_worker_api.get_training_task_params')
    def test_get_training_task_params_api_error(self, mock_call):
        mock_call.side_effect = AITrainingRequestError("Test error!")
        with self.assert_retry(train_classifiers, AITrainingRequestError):
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
        self._set_algorithm_id(ERROR_STUB_ALGORITHM_ID)
        with self.assert_retry(train_classifiers, TrainingError):
            train_classifiers(self.workflow_uuid)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @mock.patch('openassessment.assessment.worker.training.ai_worker_api.create_classifiers')
    def test_create_classifiers_api_error(self, mock_call):
        mock_call.side_effect = AITrainingRequestError("Test error!")
        with self.assert_retry(train_classifiers, AITrainingRequestError):
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
            with self.assert_retry(train_classifiers, InvalidExample):
                train_classifiers(self.workflow_uuid)


class AIGradingTaskTest(CeleryTaskTest):
    """
    Tests for the grading task executed asynchronously by Celery workers.
    """

    # Classifier data
    # Since this is controlled by the AI algorithm implementation,
    # we could put anything here as long as it's JSON-serializable.
    CLASSIFIERS = {
        u"vøȼȺƀᵾłȺɍɏ": {
            'name': u'𝒕𝒆𝒔𝒕 𝒄𝒍𝒂𝒔𝒔𝒊𝒇𝒊𝒆𝒓',
            'data': u'Öḧ ḷëẗ ẗḧë ṡüṅ ḅëäẗ ḋöẅṅ üṗöṅ ṁÿ ḟäċë, ṡẗäṛṡ ẗö ḟïḷḷ ṁÿ ḋṛëäṁ"'
        },
        u"ﻭɼค๓๓คɼ": {
            'name': u'𝒕𝒆𝒔𝒕 𝒄𝒍𝒂𝒔𝒔𝒊𝒇𝒊𝒆𝒓',
            'data': u"І ам а тѓаvэlэѓ оf ъотЂ тімэ аиↁ ѕрасэ, то ъэ шЂэѓэ І Ђаvэ ъээи"
        }
    }

    def setUp(self):
        """
        Create a submission and grading workflow.
        """
        # Create a submission
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER)
        self.submission_uuid = submission['uuid']

        # Create a workflow for the submission
        workflow = AIGradingWorkflow.start_workflow(self.submission_uuid, RUBRIC, ALGORITHM_ID)
        self.workflow_uuid = workflow.uuid

        # Associate the workflow with classifiers
        rubric = rubric_from_dict(RUBRIC)
        classifier_set = AIClassifierSet.create_classifier_set(
            self.CLASSIFIERS, rubric, ALGORITHM_ID, STUDENT_ITEM.get('course_id'), STUDENT_ITEM.get('item_id')
        )
        workflow.classifier_set = classifier_set
        workflow.save()

    @mock.patch('openassessment.assessment.api.ai_worker.create_assessment')
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_algorithm_gives_invalid_score(self, mock_create_assessment):
        # If an algorithm provides a score that isn't in the rubric,
        # we should choose the closest valid score.
        self._set_algorithm_id(INVALID_SCORE_ALGORITHM_ID)

        # The first score given by the algorithm should be below the minimum valid score
        # The second score will be between two valid scores (0 and 1), rounding up
        grade_essay(self.workflow_uuid)
        expected_scores = {
            u"vøȼȺƀᵾłȺɍɏ": 0,
            u"ﻭɼค๓๓คɼ": 1
        }
        mock_create_assessment.assert_called_with(self.workflow_uuid, expected_scores)

        # The third score will be between two valid scores (1 and 2), rounding down
        # The final score will be greater than the maximum score
        self._reset_workflow()
        grade_essay(self.workflow_uuid)
        expected_scores = {
            u"vøȼȺƀᵾłȺɍɏ": 1,
            u"ﻭɼค๓๓คɼ": 2
        }
        mock_create_assessment.assert_called_with(self.workflow_uuid, expected_scores)

    @mock.patch('openassessment.assessment.worker.grading.ai_worker_api.get_grading_task_params')
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_retrieve_params_error(self, mock_call):
        mock_call.side_effect = AIGradingInternalError("Test error")
        with self.assert_retry(grade_essay, AIGradingInternalError):
            grade_essay(self.workflow_uuid)

    def test_unknown_algorithm_id_error(self):
        # Since we're not overriding settings, the algorithm ID won't be recognized
        with self.assert_retry(grade_essay, UnknownAlgorithm):
            grade_essay(self.workflow_uuid)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_algorithm_score_error(self):
        self._set_algorithm_id(ERROR_STUB_ALGORITHM_ID)
        with self.assert_retry(grade_essay, ScoreError):
            grade_essay(self.workflow_uuid)

    @mock.patch('openassessment.assessment.worker.grading.ai_worker_api.create_assessment')
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_create_assessment_error(self, mock_call):
        mock_call.side_effect = AIGradingInternalError
        with self.assert_retry(grade_essay, AIGradingInternalError):
            grade_essay(self.workflow_uuid)

    @mock.patch('openassessment.assessment.worker.grading.ai_worker_api.get_grading_task_params')
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_params_missing_criterion_for_valid_scores(self, mock_call):
        mock_call.return_value = {
            'essay_text': 'test',
            'classifier_set': {
                u"vøȼȺƀᵾłȺɍɏ": {},
                u"ﻭɼค๓๓คɼ": {}
            },
            'algorithm_id': ALGORITHM_ID,
            'valid_scores': {}
        }
        with self.assert_retry(grade_essay, AIGradingInternalError):
            grade_essay(self.workflow_uuid)

    @mock.patch('openassessment.assessment.worker.grading.ai_worker_api.get_grading_task_params')
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_params_valid_scores_empty_list(self, mock_call):
        mock_call.return_value = {
            'essay_text': 'test',
            'classifier_set': {
                u"vøȼȺƀᵾłȺɍɏ": {},
                u"ﻭɼค๓๓คɼ": {}
            },
            'algorithm_id': ALGORITHM_ID,
            'valid_scores': {
                u"vøȼȺƀᵾłȺɍɏ": [],
                u"ﻭɼค๓๓คɼ": [0, 1, 2]
            }
        }
        with self.assert_retry(grade_essay, AIGradingInternalError):
            grade_essay(self.workflow_uuid)

    def _set_algorithm_id(self, algorithm_id):
        """
        Override the default algorithm ID for the grading workflow.

        Args:
            algorithm_id (unicode): The new algorithm ID

        Returns:
            None

        """
        workflow = AIGradingWorkflow.objects.get(uuid=self.workflow_uuid)
        workflow.algorithm_id = algorithm_id
        workflow.save()

    def _reset_workflow(self):
        """
        Reset the workflow so we can re-use it.
        """
        workflow = AIGradingWorkflow.objects.get(uuid=self.workflow_uuid)
        workflow.completed_at = None
        workflow.assessment = None
        workflow.save()
