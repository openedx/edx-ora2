# coding=utf-8
"""
Tests for AI assessment.
"""
import copy
import mock
from django.db import DatabaseError
from django.test.utils import override_settings
from openassessment.test_utils import CacheResetTest
from submissions import api as sub_api
from openassessment.assessment.api import ai as ai_api
from openassessment.assessment.models import (
    AITrainingWorkflow, AIGradingWorkflow, AIClassifierSet, Assessment
)
from openassessment.assessment.worker.algorithm import AIAlgorithm
from openassessment.assessment.serializers import rubric_from_dict
from openassessment.assessment.errors import (
    AITrainingRequestError, AITrainingInternalError,
    AIGradingRequestError, AIGradingInternalError
)
from openassessment.assessment.test.constants import RUBRIC, EXAMPLES, STUDENT_ITEM, ANSWER


class StubAIAlgorithm(AIAlgorithm):
    """
    Stub implementation of a supervised ML algorithm.
    """
    # The format of the serialized classifier is controlled
    # by the AI algorithm implementation, so we can return
    # anything here as long as it's JSON-serializable
    FAKE_CLASSIFIER = {
        'name': u'ƒαкє ¢ℓαѕѕιƒιєя',
        'binary_content': "TWFuIGlzIGRpc3Rpbmd1aX"
    }

    def train_classifier(self, examples):
        """
        Stub implementation that returns fake classifier data.
        """
        # Include the input essays in the classifier
        # so we can test that the correct inputs were used
        classifier = copy.copy(self.FAKE_CLASSIFIER)
        classifier['examples'] = examples
        classifier['score_override'] = 0
        return classifier

    def score(self, text, classifier):
        """
        Stub implementation that returns whatever scores were
        provided in the serialized classifier data.

        Expect `classifier` to be a dict with a single key,
        "score_override" containing the score to return.
        """
        return classifier['score_override']


ALGORITHM_ID = "test-stub"

AI_ALGORITHMS = {
    ALGORITHM_ID: '{module}.StubAIAlgorithm'.format(module=__name__),
}


class AITrainingTest(CacheResetTest):
    """
    Tests for AI training tasks.
    """

    EXPECTED_INPUT_SCORES = {
        u'vøȼȺƀᵾłȺɍɏ': [1, 0],
        u'ﻭɼค๓๓คɼ': [0, 2]
    }

    # Use a stub AI algorithm
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_train_classifiers(self):
        # Schedule a training task
        # Because Celery is configured in "always eager" mode,
        # expect the task to be executed synchronously.
        workflow_uuid = ai_api.train_classifiers(RUBRIC, EXAMPLES, ALGORITHM_ID)

        # Retrieve the classifier set from the database
        workflow = AITrainingWorkflow.objects.get(uuid=workflow_uuid)
        classifier_set = workflow.classifier_set
        self.assertIsNot(classifier_set, None)

        # Retrieve a dictionary mapping criteria names to deserialized classifiers
        classifiers = classifier_set.classifiers_dict

        # Check that we have classifiers for all criteria in the rubric
        criteria = set(criterion['name'] for criterion in RUBRIC['criteria'])
        self.assertEqual(set(classifiers.keys()), criteria)

        # Check that the classifier data matches the data from our stub AI algorithm
        # Since the stub data includes the training examples, we also verify
        # that the classifier was trained using the correct examples.
        for criterion in RUBRIC['criteria']:
            classifier = classifiers[criterion['name']]
            self.assertEqual(classifier['name'], StubAIAlgorithm.FAKE_CLASSIFIER['name'])
            self.assertEqual(classifier['binary_content'], StubAIAlgorithm.FAKE_CLASSIFIER['binary_content'])

            # Verify that the correct essays and scores were used to create the classifier
            # Our stub AI algorithm provides these for us, but they would not ordinarily
            # be included in the trained classifier.
            self.assertEqual(len(classifier['examples']), len(EXAMPLES))
            expected_scores = self.EXPECTED_INPUT_SCORES[criterion['name']]
            for data in zip(EXAMPLES, classifier['examples'], expected_scores):
                sent_example, received_example, expected_score = data
                received_example = AIAlgorithm.ExampleEssay(*received_example)
                self.assertEqual(received_example.text, sent_example['answer'])
                self.assertEqual(received_example.score, expected_score)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_train_classifiers_invalid_examples(self):
        # Mutate an example so it does not match the rubric
        mutated_examples = copy.deepcopy(EXAMPLES)
        mutated_examples[0]['options_selected'] = {'invalid': 'invalid'}

        # Expect a request error
        with self.assertRaises(AITrainingRequestError):
            ai_api.train_classifiers(RUBRIC, mutated_examples, ALGORITHM_ID)

    def test_train_classifiers_no_examples(self):
        # Empty list of training examples
        with self.assertRaises(AITrainingRequestError):
            ai_api.train_classifiers(RUBRIC, [], ALGORITHM_ID)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @mock.patch.object(AITrainingWorkflow.objects, 'create')
    def test_start_workflow_database_error(self, mock_create):
        # Simulate a database error when creating the training workflow
        mock_create.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AITrainingInternalError):
            ai_api.train_classifiers(RUBRIC, EXAMPLES, ALGORITHM_ID)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @mock.patch('openassessment.assessment.api.ai.training_tasks')
    def test_schedule_training_error(self, mock_training_tasks):
        # Simulate an exception raised when scheduling a training task
        mock_training_tasks.train_classifiers.apply_async.side_effect = Exception("KABOOM!")
        with self.assertRaises(AITrainingInternalError):
            ai_api.train_classifiers(RUBRIC, EXAMPLES, ALGORITHM_ID)


class AIGradingTest(CacheResetTest):
    """
    Tests for AI grading tasks.
    """

    CLASSIFIER_SCORE_OVERRIDES = {
        u"vøȼȺƀᵾłȺɍɏ": {'score_override': 1},
        u"ﻭɼค๓๓คɼ": {'score_override': 2}
    }

    def setUp(self):
        """
        Create a submission and a fake classifier set.
        """
        # Create a submission
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER)
        self.submission_uuid = submission['uuid']

        # Create the classifier set for our fake AI algorithm
        # To isolate these tests from the tests for the training
        # task, we use the database models directly.
        # We also use a stub AI algorithm that simply returns
        # whatever scores we specify in the classifier data.
        rubric = rubric_from_dict(RUBRIC)
        AIClassifierSet.create_classifier_set(
            self.CLASSIFIER_SCORE_OVERRIDES, rubric, ALGORITHM_ID
        )

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_grade_essay(self):
        # Schedule a grading task
        # Because Celery is configured in "always eager" mode, this will
        # be executed synchronously.
        ai_api.submit(self.submission_uuid, RUBRIC, ALGORITHM_ID)

        # Verify that we got the scores we provided to the stub AI algorithm
        assessment = ai_api.get_latest_assessment(self.submission_uuid)
        for part in assessment['parts']:
            criterion_name = part['option']['criterion']['name']
            expected_score = self.CLASSIFIER_SCORE_OVERRIDES[criterion_name]['score_override']
            self.assertEqual(part['option']['points'], expected_score)

    @mock.patch('openassessment.assessment.api.ai.grading_tasks.grade_essay')
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_submit_no_classifiers_available(self, mock_task):
        # Use a rubric that does not have classifiers available
        new_rubric = copy.deepcopy(RUBRIC)
        new_rubric['criteria'] = new_rubric['criteria'][1:]

        # Submit the essay -- since there are no classifiers available,
        # the workflow should be created, but no task should be scheduled.
        workflow_uuid = ai_api.submit(self.submission_uuid, new_rubric, ALGORITHM_ID)

        # Verify that the workflow was created with a null classifier set
        workflow = AIGradingWorkflow.objects.get(uuid=workflow_uuid)
        self.assertIs(workflow.classifier_set, None)

        # Verify that there are no assessments
        latest_assessment = ai_api.get_latest_assessment(self.submission_uuid)
        self.assertIs(latest_assessment, None)

        # Verify that the task was never scheduled
        self.assertFalse(mock_task.apply_async.called)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_submit_submission_not_found(self):
        with self.assertRaises(AIGradingRequestError):
            ai_api.submit("no_such_submission", RUBRIC, ALGORITHM_ID)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_submit_invalid_rubric(self):
        invalid_rubric = {'not_valid': True}
        with self.assertRaises(AIGradingRequestError):
            ai_api.submit(self.submission_uuid, invalid_rubric, ALGORITHM_ID)

    @mock.patch.object(AIGradingWorkflow.objects, 'create')
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_submit_database_error(self, mock_call):
        mock_call.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AIGradingInternalError):
            ai_api.submit(self.submission_uuid, RUBRIC, ALGORITHM_ID)

    @mock.patch('openassessment.assessment.api.ai.grading_tasks.grade_essay')
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_grade_task_schedule_error(self, mock_task):
        mock_task.apply_async.side_effect = IOError("Test error!")
        with self.assertRaises(AIGradingInternalError):
            ai_api.submit(self.submission_uuid, RUBRIC, ALGORITHM_ID)

    @mock.patch.object(Assessment.objects, 'filter')
    def test_get_latest_assessment_database_error(self, mock_call):
        mock_call.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AIGradingInternalError):
            ai_api.get_latest_assessment(self.submission_uuid)
