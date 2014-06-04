# coding=utf-8
"""
Tests for AI assessment.
"""
import copy
import mock
from nose.tools import raises
from django.db import DatabaseError
from django.test.utils import override_settings
from openassessment.test_utils import CacheResetTest
from submissions import api as sub_api
from openassessment.assessment.api import ai as ai_api

from openassessment.assessment.models import (
    AITrainingWorkflow, AIGradingWorkflow, AIClassifierSet, Assessment
)

from openassessment.assessment.models import AITrainingWorkflow, AIGradingWorkflow, AIClassifierSet
from openassessment.assessment.worker.algorithm import AIAlgorithm, AIAlgorithmError
from openassessment.assessment.serializers import rubric_from_dict
from openassessment.assessment.errors import (
    AITrainingRequestError, AITrainingInternalError, AIGradingRequestError, AIGradingInternalError, AIError
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
COURSE_ID = STUDENT_ITEM.get('course_id')
ITEM_ID = STUDENT_ITEM.get('item_id')

AI_ALGORITHMS = {
    ALGORITHM_ID: '{module}.StubAIAlgorithm'.format(module=__name__),
}


def train_classifiers(rubric_dict, classifier_score_overrides):
    """
    Simple utility function to train classifiers.

    Args:
        rubric_dict (dict): The rubric to train the classifiers on.
        classifier_score_overrides (dict): A dictionary of classifier overrides
            to set the scores for the given submission.

    """
    rubric = rubric_from_dict(rubric_dict)
    AIClassifierSet.create_classifier_set(
        classifier_score_overrides, rubric, ALGORITHM_ID, COURSE_ID, ITEM_ID
    )


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
        workflow_uuid = ai_api.train_classifiers(RUBRIC, EXAMPLES, COURSE_ID, ITEM_ID, ALGORITHM_ID)

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
            ai_api.train_classifiers(RUBRIC, mutated_examples, COURSE_ID, ITEM_ID, ALGORITHM_ID)

    def test_train_classifiers_no_examples(self):
        # Empty list of training examples
        with self.assertRaises(AITrainingRequestError):
            ai_api.train_classifiers(RUBRIC, [], COURSE_ID, ITEM_ID, ALGORITHM_ID)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @mock.patch.object(AITrainingWorkflow.objects, 'create')
    def test_start_workflow_database_error(self, mock_create):
        # Simulate a database error when creating the training workflow
        mock_create.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AITrainingInternalError):
            ai_api.train_classifiers(RUBRIC, EXAMPLES, COURSE_ID, ITEM_ID, ALGORITHM_ID)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    @mock.patch('openassessment.assessment.api.ai.training_tasks')
    def test_schedule_training_error(self, mock_training_tasks):
        # Simulate an exception raised when scheduling a training task
        mock_training_tasks.train_classifiers.apply_async.side_effect = AITrainingRequestError("KABOOM!")
        with self.assertRaises(AITrainingInternalError):
            ai_api.train_classifiers(RUBRIC, EXAMPLES, COURSE_ID, ITEM_ID, ALGORITHM_ID)


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

        train_classifiers(RUBRIC, self.CLASSIFIER_SCORE_OVERRIDES)

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

        score = ai_api.get_score(self.submission_uuid, {})
        self.assertEquals(score["points_possible"], 4)
        self.assertEquals(score["points_earned"], 3)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_get_assessment_scores_by_criteria(self):
        ai_api.submit(self.submission_uuid, RUBRIC, ALGORITHM_ID)

        # Verify that we got the scores we provided to the stub AI algorithm
        assessment = ai_api.get_latest_assessment(self.submission_uuid)
        assessment_score_dict = ai_api.get_assessment_scores_by_criteria(self.submission_uuid)
        for part in assessment['parts']:
            criterion_name = part['option']['criterion']['name']
            expected_score = self.CLASSIFIER_SCORE_OVERRIDES[criterion_name]['score_override']
            self.assertEqual(assessment_score_dict[criterion_name], expected_score)

    @raises(ai_api.AIGradingInternalError)
    @mock.patch.object(Assessment.objects, 'filter')
    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_error_getting_assessment_scores(self, mock_filter):
        mock_filter.side_effect = DatabaseError("Oh no!")
        ai_api.get_assessment_scores_by_criteria(self.submission_uuid)

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


class AIUntrainedGradingTest:
    """
    Tests that do not run the setup to train classifiers.

    """

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_no_score(self):
        # Test that no score has been created, and get_score returns None.
        ai_api.submit(self.submission_uuid, RUBRIC, ALGORITHM_ID)
        score = ai_api.get_score(self.submission_uuid, {})
        self.assertIsNone(score)


class AIReschedulingTest(CacheResetTest):
    """
    Tests AI rescheduling.

    Tests in both orders, and tests all error conditions that can arise as a result of calling rescheduling
    """


    def setUp(self):
        """
        Sets up each test so that it will have unfinished tasks of both types
        """
        # 1) Schedule Grading, have the scheduling succeeed but the grading fail because no classifiers exist
        for i in range(0, 10):
            submission = sub_api.create_submission(STUDENT_ITEM, ANSWER)
            self.submission_uuid = submission['uuid']
            ai_api.submit(self.submission_uuid, RUBRIC, ALGORITHM_ID)

        # 2) Schedule Training, have it INTENTIONALLY fail. Now we are a point where both parts need to be rescheduled
        patched_method = 'openassessment.assessment.api.ai.training_tasks.train_classifiers.apply_async'
        with mock.patch(patched_method) as mock_train_classifiers:
            mock_train_classifiers.side_effect = AITrainingInternalError('Training Classifiers Failed for some Reason.')
            with self.assertRaises(AITrainingInternalError):
                ai_api.train_classifiers(RUBRIC, EXAMPLES, COURSE_ID, ITEM_ID, ALGORITHM_ID)

        self._assert_complete(training_done=False, grading_done=False)

    def _assert_complete(self, training_done=None, grading_done=None):
        """
        Asserts that the Training and Grading are of a given completion status
        Serves as an assertion for a number of unit tests.

        Args:
            training_done (bool): whether the user expects there to be unfinished training workflows
            grading_done (bool): whether the user expects there to be unfinished grading workflows
        """
        incomplete_training_workflows = AITrainingWorkflow.get_incomplete_workflows(course_id=COURSE_ID,item_id=ITEM_ID)
        incomplete_grading_workflows = AIGradingWorkflow.get_incomplete_workflows(course_id=COURSE_ID, item_id=ITEM_ID)
        if training_done is not None:
            self.assertEqual(self._is_empty_generator(incomplete_training_workflows), training_done)
        if grading_done is not None:
            self.assertEqual(self._is_empty_generator(incomplete_grading_workflows), grading_done)

    def _is_empty_generator(self, gen):
        """
        Tests whether a given generator has any more output.
        Consumes a unit of output in test.

        Args:
            gen (generator): A generator to test if empty

        Returns:
            (bool): whether or not the generator contained output before testing
        """
        try:
            next(gen)
            return False
        except StopIteration:
            return True

    def _call_reschedule_safe(self, task_type=u"grade"):
        """
        A method which will reject an exception thrown by the unfinished task API.

        This method is necessary because when we set our celery workers to propogate all errors upward
        (as we now do in our unit testing suite), that also means that when a task fails X times (say
        a grading task fails because classifiers are not defined) that exception will be retruned from
        the call of the grade_essay (even though asynchronous), and peroclate up.  This method is used
        to agknowledge the fact that we expect there to be an error, and allow us to call reschedule
        unfinished tasks without catching that error directly.

        Args:
            task_type (unicode): describes what tasks we should reschedule
        """
        try:
            ai_api.reschedule_unfinished_tasks(course_id=COURSE_ID, item_id=ITEM_ID, task_type=task_type)
        except Exception as ex:
            # This exception is being raised because of a timeout.
            pass

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_reschedule_grading_success(self):
        # Rescheduling grading only, expect no successes
        self._call_reschedule_safe(task_type=u"grade")

        # Neither training nor grading should be complete.
        self._assert_complete(grading_done=False, training_done=False)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_reschedule_training_success(self):
        # Reschedule training, expect all successes
        ai_api.reschedule_unfinished_tasks(course_id=COURSE_ID, item_id=ITEM_ID, task_type=u"train")

        # Both training and grading should be complete.
        self._assert_complete(grading_done=True, training_done=True)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_reschedule_training_success(self):
        # Reschedule everything, expect all successes
        ai_api.reschedule_unfinished_tasks(course_id=COURSE_ID, item_id=ITEM_ID, task_type=None)

        # Both training and grading should be complete.
        self._assert_complete(grading_done=True, training_done=True)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_reschedule_database_failure(self):
        # 3) Mock in a DB error.
        patched_method = 'openassessment.assessment.worker.grading.AIGradingWorkflow.objects.filter'
        with mock.patch(patched_method) as mock_filter:
            mock_filter.side_effect = DatabaseError('DB ERROR: KABOOM')
            with self.assertRaises(AIGradingInternalError):
                ai_api.reschedule_unfinished_tasks(course_id=COURSE_ID, item_id=ITEM_ID, task_type=None)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_reschedule_grade_failure(self):
        # Mock in consistent failure to grade an essay
        with mock.patch('openassessment.assessment.worker.grading.grade_essay.apply_async') as mock_grade_essay:
            mock_grade_essay.side_effect = AIGradingInternalError("Sorry, no grade for you.")
            with self.assertRaises(AIGradingInternalError):
                # Try to reschedule all unfinished tasks, expect an internal grading error
                ai_api.reschedule_unfinished_tasks(course_id=COURSE_ID, item_id=ITEM_ID, task_type=None)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_reschedule_train_failure(self):
        # Mock in consistent failure to grade an essay
        with mock.patch('openassessment.assessment.worker.training.train_classifiers.apply_async') as mock_train:
            mock_train.side_effect = AITrainingInternalError("OH MY! THE TRAINing DERAILED!")
            with self.assertRaises(AITrainingInternalError):
                # Try to reschedule all unfinished tasks, expect an internal tra error
                ai_api.reschedule_unfinished_tasks(course_id=COURSE_ID, item_id=ITEM_ID, task_type=u"train")

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_reschedule_non_valid_args(self):
        with self.assertRaises(AIError):
            ai_api.reschedule_unfinished_tasks(course_id=COURSE_ID, task_type=u"train")

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_reschedule_all_large(self):
        """
        Specifically tests the querying mechanisms (python generator functions), and ensures that our methodology
        holds up for querysets with 125+ entries
        """
        # Creates 125 more grades (for a total of 135)
        for i in range(0, 125):
            submission = sub_api.create_submission(STUDENT_ITEM, ANSWER)
            self.submission_uuid = submission['uuid']
            ai_api.submit(self.submission_uuid, RUBRIC, ALGORITHM_ID)

        # Both training and grading should not be complete.
        self._assert_complete(grading_done=False, training_done=False)

        # Reschedule both
        ai_api.reschedule_unfinished_tasks(course_id=COURSE_ID, item_id=ITEM_ID, task_type=None)

        # Check that  both training and grading are now complete
        self._assert_complete(grading_done=True, training_done=True)


class AIAutomaticGradingTest(CacheResetTest):

    def _assert_complete(self, training_done=None, grading_done=None):
        """
        Asserts that the Training and Grading are of a given completion status
        Serves as an assertion for a number of unit tests.

        Args:
            training_done (bool): whether the user expects there to be unfinished training workflows
            grading_done (bool): whether the user expects there to be unfinished grading workflows
        """
        incomplete_training_workflows = AITrainingWorkflow.get_incomplete_workflows(course_id=COURSE_ID,item_id=ITEM_ID)
        incomplete_grading_workflows = AIGradingWorkflow.get_incomplete_workflows(course_id=COURSE_ID, item_id=ITEM_ID)
        if training_done is not None:
            self.assertEqual(self._is_empty_generator(incomplete_training_workflows), training_done)
        if grading_done is not None:
            self.assertEqual(self._is_empty_generator(incomplete_grading_workflows), grading_done)

    def _is_empty_generator(self, gen):
        """
        Tests whether a given generator has any more output.
        Consumes a unit of output in test.

        Args:
            gen (generator): A generator to test if empty

        Returns:
            (bool): whether or not the generator contained output before testing
        """
        try:
            next(gen)
            return False
        except StopIteration:
            return True

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_automatic_grade(self):
        # Create some submissions which will not succeed. No classifiers yet exist.
        for i in range(0, 10):
            submission = sub_api.create_submission(STUDENT_ITEM, ANSWER)
            self.submission_uuid = submission['uuid']
            ai_api.submit(self.submission_uuid, RUBRIC, ALGORITHM_ID)

        # Check that there are unresolved grading workflows
        self._assert_complete(training_done=True, grading_done=False)

        # Create and train a classifier set.  This should set off automatic grading.
        ai_api.train_classifiers(RUBRIC, EXAMPLES, COURSE_ID, ITEM_ID, ALGORITHM_ID)

        # Check to make sure that all work is done.
        self._assert_complete(training_done=True, grading_done=True)

    @override_settings(ORA2_AI_ALGORITHMS=AI_ALGORITHMS)
    def test_automatic_grade_error(self):
        # Create some submissions which will not succeed. No classifiers yet exist.
        for i in range(0, 10):
            submission = sub_api.create_submission(STUDENT_ITEM, ANSWER)
            self.submission_uuid = submission['uuid']
            ai_api.submit(self.submission_uuid, RUBRIC, ALGORITHM_ID)

        # Check that there are unresolved grading workflows
        self._assert_complete(training_done=True, grading_done=False)

        patched_method = 'openassessment.assessment.worker.training.reschedule_grading_tasks.apply_async'
        with mock.patch(patched_method) as mocked_reschedule_grading:
            mocked_reschedule_grading.side_effect = AIGradingInternalError("Kablewey.")
            with self.assertRaises(AIGradingInternalError):
                ai_api.train_classifiers(RUBRIC, EXAMPLES, COURSE_ID, ITEM_ID, ALGORITHM_ID)

