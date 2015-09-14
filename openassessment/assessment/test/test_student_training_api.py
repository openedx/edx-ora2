# -*- coding: utf-8 -*-
"""
Tests for training assessment type.
"""
import copy
from django.db import DatabaseError
import ddt
from mock import patch
from openassessment.test_utils import CacheResetTest
from .constants import STUDENT_ITEM, ANSWER, RUBRIC, EXAMPLES
from submissions import api as sub_api
from openassessment.assessment.api import student_training as training_api
from openassessment.assessment.errors import StudentTrainingRequestError, StudentTrainingInternalError
from openassessment.assessment.models import StudentTrainingWorkflow


@ddt.ddt
class StudentTrainingAssessmentTest(CacheResetTest):
    """
    Tests for the training assessment type.
    """
    longMessage = True

    def setUp(self):
        """
        Create a submission.
        """
        submission = sub_api.create_submission(STUDENT_ITEM, ANSWER)
        training_api.on_start(submission['uuid'])
        self.submission_uuid = submission['uuid']

    def test_training_workflow(self):
        # Initially, we should be on the first step
        self._assert_workflow_status(self.submission_uuid, 0, 2)

        # Get a training example
        self._assert_get_example(self.submission_uuid, 0, EXAMPLES, RUBRIC)

        # Assess the training example the same way the instructor did
        corrections = training_api.assess_training_example(
            self.submission_uuid,
            EXAMPLES[0]['options_selected']
        )
        self.assertEqual(corrections, dict())
        self._assert_workflow_status(self.submission_uuid, 1, 2)

        # Get another training example to assess
        self._assert_get_example(self.submission_uuid, 1, EXAMPLES, RUBRIC)

        # Give the example different scores than the instructor gave
        incorrect_assessment = {
            u"vøȼȺƀᵾłȺɍɏ": u"𝓰𝓸𝓸𝓭",
            u"ﻭɼค๓๓คɼ": u"𝓰𝓸𝓸𝓭",
        }
        corrections = training_api.assess_training_example(
            self.submission_uuid, incorrect_assessment
        )

        # Expect that we get corrected and stay on the current example
        self.assertItemsEqual(corrections, EXAMPLES[1]['options_selected'])
        self._assert_workflow_status(self.submission_uuid, 1, 2)

        # Try again, and this time assess the same way as the instructor
        corrections = training_api.assess_training_example(
            self.submission_uuid, EXAMPLES[1]['options_selected']
        )
        self.assertEqual(corrections, dict())

        # Now we should have completed both assessments
        self._assert_workflow_status(self.submission_uuid, 2, 2)

    def test_assess_without_update(self):
        # Assess the first training example the same way the instructor did
        # but do NOT update the workflow
        training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)
        corrections = training_api.assess_training_example(
            self.submission_uuid,
            EXAMPLES[0]['options_selected'],
            update_workflow=False
        )

        # Expect that we're still on the first step
        self.assertEqual(corrections, dict())
        self._assert_workflow_status(self.submission_uuid, 0, 2)

    def test_get_same_example(self):
        # Retrieve a training example
        retrieved = training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)

        # If we retrieve an example without completing the current example,
        # we should get the same one.
        next_retrieved = training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)
        self.assertEqual(retrieved, next_retrieved)

    def test_get_training_example_num_queries(self):

        # Run through the training example once using a different submission
        # Training examples and rubrics will be cached and shared for other
        # students working on the same problem.
        self._warm_cache(RUBRIC, EXAMPLES)

        # First training example
        # This will need to create the student training workflow and the first item
        # NOTE: we *could* cache the rubric model to reduce the number of queries here,
        # but we're selecting it by content hash, which is indexed and should be plenty fast.
        with self.assertNumQueries(6):
            training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)

        # Without assessing the first training example, try to retrieve a training example.
        # This should return the same example as before, so we won't need to create
        # any workflows or workflow items.
        with self.assertNumQueries(5):
            training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)

        # Assess the current training example
        training_api.assess_training_example(self.submission_uuid, EXAMPLES[0]['options_selected'])

        # Retrieve the next training example, which requires us to create
        # a new workflow item (but not a new workflow).
        with self.assertNumQueries(6):
            training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)

    def test_submitter_is_finished_num_queries(self):
        # Complete the first training example
        training_api.on_start(self.submission_uuid)
        training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)
        training_api.assess_training_example(self.submission_uuid, EXAMPLES[0]['options_selected'])

        # Check whether we've completed the requirements
        requirements = {'num_required': 2}
        with self.assertNumQueries(2):
            training_api.submitter_is_finished(self.submission_uuid, requirements)

    def test_get_num_completed_num_queries(self):
        # Complete the first training example
        training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)
        training_api.assess_training_example(self.submission_uuid, EXAMPLES[0]['options_selected'])

        # Check the number completed
        with self.assertNumQueries(2):
            training_api.get_num_completed(self.submission_uuid)

    def test_assess_training_example_num_queries(self):
        # Populate the cache with training examples and rubrics
        self._warm_cache(RUBRIC, EXAMPLES)
        training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)
        with self.assertNumQueries(3):
            training_api.assess_training_example(self.submission_uuid, EXAMPLES[0]['options_selected'])

    @ddt.file_data('data/validate_training_examples.json')
    def test_validate_training_examples(self, data):
        errors = training_api.validate_training_examples(
            data['rubric'], data['examples']
        )
        msg = u"Expected errors {} but got {}".format(data['errors'], errors)
        self.assertItemsEqual(errors, data['errors'], msg=msg)

    def test_is_finished_no_workflow(self):
        # Without creating a workflow, we should not be finished
        requirements = {'num_required': 1}
        self.assertFalse(training_api.submitter_is_finished(self.submission_uuid, requirements))

    def test_get_training_example_none_available(self):
        for example in EXAMPLES:
            training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)
            training_api.assess_training_example(self.submission_uuid, example['options_selected'])

        # Now we should be complete
        self._assert_workflow_status(self.submission_uuid, 2, 2)

        # ... and if we try to get another example, we should get None
        self.assertIs(
            training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES),
            None
        )

    def test_assess_training_example_completed_workflow(self):
        for example in EXAMPLES:
            training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)
            training_api.assess_training_example(self.submission_uuid, example['options_selected'])

        # Try to assess again, and expect an error
        with self.assertRaises(StudentTrainingRequestError):
            training_api.assess_training_example(
                self.submission_uuid, EXAMPLES[0]['options_selected']
            )

    def test_assess_training_example_no_workflow(self):
        # If we try to assess without first retrieving an example
        # (which implicitly creates a workflow)
        # then we should get a request error.
        with self.assertRaises(StudentTrainingRequestError):
            training_api.assess_training_example(
                self.submission_uuid, EXAMPLES[0]['options_selected']
            )

    def test_get_num_completed_no_workflow(self):
        num_completed = training_api.get_num_completed(self.submission_uuid)
        self.assertEqual(num_completed, 0)

    def test_get_training_example_invalid_rubric(self):
        # Rubric is missing a very important key!
        invalid_rubric = copy.deepcopy(RUBRIC)
        del invalid_rubric['criteria']

        with self.assertRaises(StudentTrainingRequestError):
            training_api.get_training_example(self.submission_uuid, invalid_rubric, EXAMPLES)

    def test_get_training_example_no_submission(self):
        with self.assertRaises(StudentTrainingRequestError):
            training_api.get_training_example("no_such_submission", RUBRIC, EXAMPLES)

    @patch.object(StudentTrainingWorkflow.objects, 'get')
    def test_get_num_completed_database_error(self, mock_db):
        mock_db.side_effect = DatabaseError("Kaboom!")
        with self.assertRaises(StudentTrainingInternalError):
            training_api.get_num_completed(self.submission_uuid)

    @patch.object(StudentTrainingWorkflow.objects, 'get')
    def test_get_training_example_database_error(self, mock_db):
        mock_db.side_effect = DatabaseError("Kaboom!")
        with self.assertRaises(StudentTrainingInternalError):
            training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)

    def test_assess_training_example_database_error(self):
        training_api.get_training_example(self.submission_uuid, RUBRIC, EXAMPLES)
        with patch.object(StudentTrainingWorkflow.objects, 'get') as mock_db:
            mock_db.side_effect = DatabaseError("Kaboom!")
            with self.assertRaises(StudentTrainingInternalError):
                training_api.assess_training_example(self.submission_uuid, EXAMPLES[0]['options_selected'])

    @ddt.data({}, {'num_required': 'not an integer!'})
    def test_submitter_is_finished_invalid_requirements(self, requirements):
        with self.assertRaises(StudentTrainingRequestError):
            training_api.submitter_is_finished(self.submission_uuid, requirements)

    def _assert_workflow_status(self, submission_uuid, num_completed, num_required):
        """
        Check that the training workflow is on the expected step.

        Args:
            submission_uuid (str): Submission UUID of the student being trained.
            num_completed (int): The expected number of examples assessed correctly.
            num_total (int): The required number of examples to assess.

        Returns:
            None

        Raises:
            AssertionError

        """
        # Check the number of steps we've completed
        actual_num_completed = training_api.get_num_completed(submission_uuid)
        self.assertEqual(actual_num_completed, num_completed)

        # Check whether the assessment step is completed
        # (used by the workflow API)
        requirements = {'num_required': num_required}
        is_finished = training_api.submitter_is_finished(submission_uuid, requirements)
        self.assertEqual(is_finished, bool(num_completed >= num_required))

    def _expected_example(self, input_example, rubric):
        """
        Return the training example we would expect to retrieve for an example.
        The retrieved example will include the rubric.

        Args:
            input_example (dict): The example dict we passed to the API.
            rubric (dict): The rubric for the example.

        Returns:
            dict

        """
        output_dict = copy.deepcopy(input_example)
        output_dict['rubric'] = rubric
        return output_dict

    def _assert_get_example(self, submission_uuid, order_num, input_examples, input_rubric):
        """
        Check the training example we get from the API.

        Args:
            submission_uuid (str): The submission UUID associated with the student being trained.
            order_num (int): The order number of the example we expect to retrieve.
            input_examples (list of dict): The examples we used to configure the training workflow.
            input_rubric (dict): The rubric we used to configure the training workflow.

        Returns:
            None

        Raises:
            AssertionError

        """
        example = training_api.get_training_example(submission_uuid, input_rubric, input_examples)
        expected_example = self._expected_example(input_examples[order_num], input_rubric)
        self.assertItemsEqual(example, expected_example)

    def _warm_cache(self, rubric, examples):
        """
        Create a submission and complete student training.
        This will populate the cache with training examples and rubrics,
        which are immutable and shared for all students training on a particular problem.

        Args:
            rubric (dict): Serialized rubric model.
            examples (list of dict): Serialized training examples

        Returns:
            None

        """
        pre_submission = sub_api.create_submission(STUDENT_ITEM, ANSWER)
        training_api.on_start(pre_submission['uuid'])
        for example in examples:
            training_api.get_training_example(pre_submission['uuid'], rubric, examples)
            training_api.assess_training_example(pre_submission['uuid'], example['options_selected'])
