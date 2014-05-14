# -*- coding: utf-8 -*-
"""
Tests for training assessment type.
"""
import copy
from django.db import DatabaseError
import ddt
from mock import patch
from openassessment.test_utils import CacheResetTest
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

    STUDENT_ITEM = {
        'student_id': u'𝓽𝓮𝓼𝓽 𝓼𝓽𝓾𝓭𝓮𝓷𝓽',
        'item_id': u'𝖙𝖊𝖘𝖙 𝖎𝖙𝖊𝖒',
        'course_id': u'ՇєรՇ ς๏ยгรє',
        'item_type': u'openassessment'
    }

    ANSWER = u'ẗëṡẗ äṅṡẅëṛ'

    RUBRIC_OPTIONS = [
        {
            "order_num": 0,
            "name": u"𝒑𝒐𝒐𝒓",
            "explanation": u"𝕻𝖔𝖔𝖗 𝖏𝖔𝖇!",
            "points": 0,
        },
        {
            "order_num": 1,
            "name": u"𝓰𝓸𝓸𝓭",
            "explanation": u"ﻭѻѻɗ ﻝѻ๒!",
            "points": 1,
        },
        {
            "order_num": 2,
            "name": "єχ¢єℓℓєηт",
            "explanation": "乇ﾒc乇ﾚﾚ乇刀ｲ ﾌo乃!",
            "points": 2,
        },
    ]

    RUBRIC = {
        'prompt': u"МоъЎ-ↁіск; оѓ, ГЂэ ЩЂаlэ",
        'criteria': [
            {
                "order_num": 0,
                "name": u"vøȼȺƀᵾłȺɍɏ",
                "prompt": u"Ħøw vȺɍɨɇđ ɨs ŧħɇ vøȼȺƀᵾłȺɍɏ?",
                "options": RUBRIC_OPTIONS
            },
            {
                "order_num": 1,
                "name": u"ﻭɼค๓๓คɼ",
                "prompt": u"𝕳𝖔𝖜 𝖈𝖔𝖗𝖗𝖊𝖈𝖙 𝖎𝖘 𝖙𝖍𝖊 𝖌𝖗𝖆𝖒𝖒𝖆𝖗?",
                "options": RUBRIC_OPTIONS
            }
        ]
    }

    EXAMPLES = [
        {
            'answer': (
                u"𝕿𝖍𝖊𝖗𝖊 𝖆𝖗𝖊 𝖈𝖊𝖗𝖙𝖆𝖎𝖓 𝖖𝖚𝖊𝖊𝖗 𝖙𝖎𝖒𝖊𝖘 𝖆𝖓𝖉 𝖔𝖈𝖈𝖆𝖘𝖎𝖔𝖓𝖘 𝖎𝖓 𝖙𝖍𝖎𝖘 𝖘𝖙𝖗𝖆𝖓𝖌𝖊 𝖒𝖎𝖝𝖊𝖉 𝖆𝖋𝖋𝖆𝖎𝖗 𝖜𝖊 𝖈𝖆𝖑𝖑 𝖑𝖎𝖋𝖊"
                u" 𝖜𝖍𝖊𝖓 𝖆 𝖒𝖆𝖓 𝖙𝖆𝖐𝖊𝖘 𝖙𝖍𝖎𝖘 𝖜𝖍𝖔𝖑𝖊 𝖚𝖓𝖎𝖛𝖊𝖗𝖘𝖊 𝖋𝖔𝖗 𝖆 𝖛𝖆𝖘𝖙 𝖕𝖗𝖆𝖈𝖙𝖎𝖈𝖆𝖑 𝖏𝖔𝖐𝖊, 𝖙𝖍𝖔𝖚𝖌𝖍 𝖙𝖍𝖊 𝖜𝖎𝖙 𝖙𝖍𝖊𝖗𝖊𝖔𝖋"
                u" 𝖍𝖊 𝖇𝖚𝖙 𝖉𝖎𝖒𝖑𝖞 𝖉𝖎𝖘𝖈𝖊𝖗𝖓𝖘, 𝖆𝖓𝖉 𝖒𝖔𝖗𝖊 𝖙𝖍𝖆𝖓 𝖘𝖚𝖘𝖕𝖊𝖈𝖙𝖘 𝖙𝖍𝖆𝖙 𝖙𝖍𝖊 𝖏𝖔𝖐𝖊 𝖎𝖘 𝖆𝖙 𝖓𝖔𝖇𝖔𝖉𝖞'𝖘 𝖊𝖝𝖕𝖊𝖓𝖘𝖊 𝖇𝖚𝖙 𝖍𝖎𝖘 𝖔𝖜𝖓."
            ),
            'options_selected': {
                u"vøȼȺƀᵾłȺɍɏ": u"𝓰𝓸𝓸𝓭",
                u"ﻭɼค๓๓คɼ": u"𝒑𝒐𝒐𝒓",
            }
        },
        {
            'answer': u"Tőṕ-héávӳ ẃáś thé śhíṕ áś á díńńéŕĺéśś śtúdéńt ẃíth áĺĺ Áŕíśtőtĺé íń híś héád.",
            'options_selected': {
                u"vøȼȺƀᵾłȺɍɏ": u"𝒑𝒐𝒐𝒓",
                u"ﻭɼค๓๓คɼ": u"єχ¢єℓℓєηт",
            }
        },
    ]

    def setUp(self):
        """
        Create a submission.
        """
        submission = sub_api.create_submission(self.STUDENT_ITEM, self.ANSWER)
        self.submission_uuid = submission['uuid']

    def test_training_workflow(self):

        # Start a workflow
        training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, self.EXAMPLES)

        # Initially, we should be on the first step
        self._assert_workflow_status(self.submission_uuid, 0, 2)

        # Get a training example
        self._assert_get_example(self.submission_uuid, 0, self.EXAMPLES, self.RUBRIC)

        # Assess the training example the same way the instructor did
        corrections = training_api.assess_training_example(
            self.submission_uuid,
            self.EXAMPLES[0]['options_selected']
        )
        self.assertEqual(corrections, dict())
        self._assert_workflow_status(self.submission_uuid, 1, 2)

        # Get another training example to assess
        self._assert_get_example(self.submission_uuid, 1, self.EXAMPLES, self.RUBRIC)

        # Give the example different scores than the instructor gave
        incorrect_assessment = {
            u"vøȼȺƀᵾłȺɍɏ": u"𝓰𝓸𝓸𝓭",
            u"ﻭɼค๓๓คɼ": u"𝓰𝓸𝓸𝓭",
        }
        corrections = training_api.assess_training_example(
            self.submission_uuid, incorrect_assessment
        )

        # Expect that we get corrected and stay on the current example
        self.assertItemsEqual(corrections, self.EXAMPLES[1]['options_selected'])
        self._assert_workflow_status(self.submission_uuid, 1, 2)

        # Try again, and this time assess the same way as the instructor
        corrections = training_api.assess_training_example(
            self.submission_uuid, self.EXAMPLES[1]['options_selected']
        )
        self.assertEqual(corrections, dict())

        # Now we should have completed both assessments
        self._assert_workflow_status(self.submission_uuid, 2, 2)

    def test_assess_without_update(self):

        # Start a workflow
        training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, self.EXAMPLES)

        # Assess the first training example the same way the instructor did
        # but do NOT update the workflow
        corrections = training_api.assess_training_example(
            self.submission_uuid,
            self.EXAMPLES[0]['options_selected'],
            update_workflow=False
        )

        # Expect that we're still on the first step
        self.assertEqual(corrections, dict())
        self._assert_workflow_status(self.submission_uuid, 0, 2)

    @ddt.file_data('data/validate_training_examples.json')
    def test_validate_training_examples(self, data):
        errors = training_api.validate_training_examples(
            data['rubric'], data['examples']
        )
        msg = u"Expected errors {} but got {}".format(data['errors'], errors)
        self.assertItemsEqual(errors, data['errors'], msg=msg)

    def test_is_finished_no_workflow(self):
        # Without creating a workflow, we should not be finished
        self.assertFalse(training_api.submitter_is_finished(self.submission_uuid, dict()))

        # But since we're not being assessed by others, the "assessment" should be finished.
        self.assertTrue(training_api.assessment_is_finished(self.submission_uuid, dict()))

    def test_get_training_example_none_available(self):
        # Start a workflow and assess all training examples
        training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, self.EXAMPLES)
        self._assert_workflow_status(self.submission_uuid, 0, 2)

        for example in self.EXAMPLES:
            training_api.assess_training_example(self.submission_uuid, example['options_selected'])

        # Now we should be complete
        self._assert_workflow_status(self.submission_uuid, 2, 2)

        # ... and if we try to get another example, we should get None
        self.assertIs(
            training_api.get_training_example(self.submission_uuid), None
        )

    def test_get_training_example_no_workflow(self):
        # With no workflow defined, we should get an error
        with self.assertRaises(StudentTrainingRequestError):
            training_api.get_training_example(self.submission_uuid)

    def test_create_training_workflow_already_started(self):
        # Create a workflow for training
        training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, self.EXAMPLES)

        # Try to create a second workflow for the same submission,
        # expecting an error.
        with self.assertRaises(StudentTrainingRequestError):
            training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, self.EXAMPLES)

    def test_create_training_workflow_no_examples(self):
        # Try to create a training workflow with no examples
        # and expect an error.
        with self.assertRaises(StudentTrainingRequestError):
            training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, [])

    def test_create_training_workflow_no_submission(self):
        # Try to create a training workflow with an invalid submission UUID
        with self.assertRaises(StudentTrainingRequestError):
            training_api.create_training_workflow("not a submission!", self.RUBRIC, self.EXAMPLES)

    def test_assess_training_example_completed_workflow(self):
        # Start a workflow and assess all training examples
        training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, self.EXAMPLES)
        self._assert_workflow_status(self.submission_uuid, 0, 2)

        for example in self.EXAMPLES:
            training_api.assess_training_example(self.submission_uuid, example['options_selected'])

        # Try to assess again, and expect an error
        with self.assertRaises(StudentTrainingRequestError):
            training_api.assess_training_example(
                self.submission_uuid, self.EXAMPLES[0]['options_selected']
            )

    def test_assess_training_example_no_workflow(self):
        # With no workflow defined, we should get an error
        with self.assertRaises(StudentTrainingRequestError):
            training_api.assess_training_example(
                self.submission_uuid, self.EXAMPLES[0]['options_selected']
            )

    def test_get_workflow_status_no_workflow(self):
        # With no workflow defined, we should get an error
        # when we try to request the status.
        with self.assertRaises(StudentTrainingRequestError):
            training_api.get_workflow_status(self.submission_uuid)

    def test_create_workflow_invalid_rubric(self):
        # Rubric is missing a very important key!
        invalid_rubric = copy.deepcopy(self.RUBRIC)
        del invalid_rubric['criteria']

        with self.assertRaises(StudentTrainingRequestError):
            training_api.create_training_workflow(self.submission_uuid, invalid_rubric, self.EXAMPLES)

    def test_create_workflow_invalid_examples(self):
        # Training example is not a dictionary!
        with self.assertRaises(StudentTrainingRequestError):
            training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, ["not a dict!"])

    @patch.object(StudentTrainingWorkflow, 'create_workflow')
    def test_create_workflow_database_error(self, mock_db):
        mock_db.side_effect = DatabaseError("Kaboom!")
        with self.assertRaises(StudentTrainingInternalError):
            training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, self.EXAMPLES)

    @patch.object(StudentTrainingWorkflow.objects, 'get')
    def test_get_workflow_status_database_error(self, mock_db):
        training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, self.EXAMPLES)
        mock_db.side_effect = DatabaseError("Kaboom!")
        with self.assertRaises(StudentTrainingInternalError):
            training_api.get_workflow_status(self.submission_uuid)

    @patch.object(StudentTrainingWorkflow.objects, 'get')
    def test_get_training_example_database_error(self, mock_db):
        training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, self.EXAMPLES)
        mock_db.side_effect = DatabaseError("Kaboom!")
        with self.assertRaises(StudentTrainingInternalError):
            training_api.get_training_example(self.submission_uuid)

    @patch.object(StudentTrainingWorkflow.objects, 'get')
    def test_assess_training_example_database_error(self, mock_db):
        training_api.create_training_workflow(self.submission_uuid, self.RUBRIC, self.EXAMPLES)
        mock_db.side_effect = DatabaseError("Kaboom!")
        with self.assertRaises(StudentTrainingInternalError):
            training_api.assess_training_example(self.submission_uuid, self.EXAMPLES[0]['options_selected'])

    def _assert_workflow_status(self, submission_uuid, num_completed, num_total):
        """
        Check that the training workflow is on the expected step.

        Args:
            submission_uuid (str): Submission UUID of the student being trained.
            num_completed (int): The expected number of examples assessed correctly.
            num_total (int): The expected number of available examples.

        Returns:
            None

        Raises:
            AssertionError

        """
        # Check the workflow status (what step are we on?)
        status = training_api.get_workflow_status(submission_uuid)
        self.assertEqual(status['num_completed'], num_completed)
        self.assertEqual(status['num_total'], num_total)

        # Check whether the assessment step is completed
        # (used by the workflow API)
        is_finished = bool(num_completed == num_total)
        self.assertEqual(
            training_api.submitter_is_finished(submission_uuid, dict()),
            is_finished
        )

        # Assessment is finished should always be true,
        # since we're not being assessed by others.
        self.assertTrue(
            training_api.assessment_is_finished(submission_uuid, dict()),
        )

        # At no point should we receive a score!
        self.assertIs(training_api.get_score(submission_uuid, dict()), None)

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
        example = training_api.get_training_example(submission_uuid)
        expected_example = self._expected_example(input_examples[order_num], input_rubric)
        self.assertItemsEqual(example, expected_example)
