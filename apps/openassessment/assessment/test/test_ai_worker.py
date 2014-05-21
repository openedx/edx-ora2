# -*- coding: utf-8 -*-
"""
Tests for AI worker API calls.
"""
import copy
import datetime
import mock
from django.db import DatabaseError
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.api import ai_worker as ai_worker_api
from openassessment.assessment.models import AITrainingWorkflow, AIClassifier
from openassessment.assessment.serializers import deserialize_training_examples
from openassessment.assessment.errors import (
    AITrainingRequestError, AITrainingInternalError
)
from openassessment.assessment.test.constants import EXAMPLES, RUBRIC


class AIWorkerTrainingTest(CacheResetTest):
    """
    Tests for the AI API calls a worker would make when
    completing a training task.
    """
    ALGORITHM_ID = "test-algorithm"

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
        Create a training workflow in the database.
        """
        examples = deserialize_training_examples(EXAMPLES, RUBRIC)
        workflow = AITrainingWorkflow.start_workflow(examples, self.ALGORITHM_ID)
        self.workflow_uuid = workflow.uuid

    def test_get_algorithm_id(self):
        algorithm_id = ai_worker_api.get_algorithm_id(self.workflow_uuid)
        self.assertEqual(algorithm_id, self.ALGORITHM_ID)

    def test_get_algorithm_id_no_workflow(self):
        with self.assertRaises(AITrainingRequestError):
            ai_worker_api.get_algorithm_id("invalid_uuid")

    @mock.patch.object(AITrainingWorkflow.objects, 'get')
    def test_get_algorithm_id_database_error(self, mock_get):
        mock_get.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AITrainingInternalError):
            ai_worker_api.get_algorithm_id(self.workflow_uuid)

    def test_get_training_examples(self):
        examples = ai_worker_api.get_training_examples(self.workflow_uuid)
        expected_examples = [
            {
                'text': EXAMPLES[0]['answer'],
                'scores': {
                    u"vøȼȺƀᵾłȺɍɏ": 1,
                    u"ﻭɼค๓๓คɼ": 0
                }
            },
            {
                'text': EXAMPLES[1]['answer'],
                'scores': {
                    u"vøȼȺƀᵾłȺɍɏ": 0,
                    u"ﻭɼค๓๓คɼ": 2
                }
            },
        ]
        self.assertItemsEqual(examples, expected_examples)

    def test_get_training_examples_no_workflow(self):
        with self.assertRaises(AITrainingRequestError):
            ai_worker_api.get_training_examples("invalid_uuid")

    @mock.patch.object(AITrainingWorkflow.objects, 'get')
    def test_get_training_examples_database_error(self, mock_get):
        mock_get.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AITrainingInternalError):
            ai_worker_api.get_training_examples(self.workflow_uuid)

    def test_create_classifiers(self):
        ai_worker_api.create_classifiers(self.workflow_uuid, self.CLASSIFIERS)

        # Expect that the workflow was marked complete
        workflow = AITrainingWorkflow.objects.get(uuid=self.workflow_uuid)
        self.assertIsNot(workflow.completed_at, None)

        # Expect that the classifier set was created with the correct data
        self.assertIsNot(workflow.classifier_set, None)
        saved_classifiers = workflow.classifier_set.classifiers_dict
        self.assertItemsEqual(self.CLASSIFIERS, saved_classifiers)

    def test_create_classifiers_no_workflow(self):
        with self.assertRaises(AITrainingRequestError):
            ai_worker_api.create_classifiers("invalid_uuid", self.CLASSIFIERS)

    @mock.patch.object(AITrainingWorkflow.objects, 'get')
    def test_create_classifiers_database_error(self, mock_get):
        mock_get.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AITrainingInternalError):
            ai_worker_api.create_classifiers(self.workflow_uuid, self.CLASSIFIERS)

    def test_create_classifiers_serialize_error(self):
        # Mutate the classifier data so it is NOT JSON-serializable
        classifiers = copy.deepcopy(self.CLASSIFIERS)
        classifiers[u"vøȼȺƀᵾłȺɍɏ"] = datetime.datetime.now()

        # Expect an error when we try to create the classifiers
        with self.assertRaises(AITrainingInternalError):
            ai_worker_api.create_classifiers(self.workflow_uuid, classifiers)

    def test_create_classifiers_missing_criteria(self):
        # Remove a criterion from the classifiers dict
        classifiers = copy.deepcopy(self.CLASSIFIERS)
        del classifiers[u"vøȼȺƀᵾłȺɍɏ"]

        # Expect an error when we try to create the classifiers
        with self.assertRaises(AITrainingRequestError):
            ai_worker_api.create_classifiers(self.workflow_uuid, classifiers)

    def test_create_classifiers_unrecognized_criterion(self):
        # Add an extra criterion to the classifiers dict
        classifiers = copy.deepcopy(self.CLASSIFIERS)
        classifiers[u"extra_criterion"] = copy.deepcopy(classifiers[u"vøȼȺƀᵾłȺɍɏ"])

        # Expect an error when we try to create the classifiers
        with self.assertRaises(AITrainingRequestError):
            ai_worker_api.create_classifiers(self.workflow_uuid, classifiers)

    @mock.patch.object(AIClassifier, 'classifier_data')
    def test_create_classifiers_upload_error(self, mock_data):
        # Simulate an error occurring when uploading the trained classifier
        mock_data.save.side_effect = IOError("OH NO!!!")
        with self.assertRaises(AITrainingInternalError):
            ai_worker_api.create_classifiers(self.workflow_uuid, self.CLASSIFIERS)

    def test_create_classifiers_twice(self):
        # Simulate repeated task execution for the same workflow
        # Since these are executed sequentially, the second call should
        # have no effect.
        ai_worker_api.create_classifiers(self.workflow_uuid, self.CLASSIFIERS)
        ai_worker_api.create_classifiers(self.workflow_uuid, self.CLASSIFIERS)

        # Expect that the workflow was marked complete
        workflow = AITrainingWorkflow.objects.get(uuid=self.workflow_uuid)
        self.assertIsNot(workflow.completed_at, None)

        # Expect that the classifier set was created with the correct data
        self.assertIsNot(workflow.classifier_set, None)
        saved_classifiers = workflow.classifier_set.classifiers_dict
        self.assertItemsEqual(self.CLASSIFIERS, saved_classifiers)

    def test_create_classifiers_no_training_examples(self):
        # Create a workflow with no training examples
        workflow = AITrainingWorkflow.objects.create(algorithm_id=self.ALGORITHM_ID)

        # Expect an error when we try to create classifiers
        with self.assertRaises(AITrainingInternalError):
            ai_worker_api.create_classifiers(workflow.uuid, self.CLASSIFIERS)
