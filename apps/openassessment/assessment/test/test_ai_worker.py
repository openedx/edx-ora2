# -*- coding: utf-8 -*-
"""
Tests for AI worker API calls.
"""
import copy
import datetime
from uuid import uuid4
import mock
from django.db import DatabaseError
from django.core.files.base import ContentFile
from submissions import api as sub_api
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.api import ai_worker as ai_worker_api
from openassessment.assessment.models import (
    AITrainingWorkflow, AIGradingWorkflow,
    AIClassifier, AIClassifierSet, Assessment
)
from openassessment.assessment.serializers import (
    rubric_from_dict, deserialize_training_examples
)
from openassessment.assessment.errors import (
    AITrainingRequestError, AITrainingInternalError,
    AIGradingRequestError, AIGradingInternalError
)
from openassessment.assessment.test.constants import (
    EXAMPLES, RUBRIC, STUDENT_ITEM, ANSWER
)

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


class AIWorkerTrainingTest(CacheResetTest):
    """
    Tests for the AI API calls a worker would make when
    completing a training task.
    """

    COURSE_ID = u"sämplë ċöürsë"
    ITEM_ID = u"12231"
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

        workflow = AITrainingWorkflow.start_workflow(examples, self.COURSE_ID, self.ITEM_ID, self.ALGORITHM_ID)

        self.workflow_uuid = workflow.uuid

    def test_get_training_task_params(self):
        params = ai_worker_api.get_training_task_params(self.workflow_uuid)
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
        self.assertItemsEqual(params['training_examples'], expected_examples)
        self.assertItemsEqual(params['algorithm_id'], ALGORITHM_ID)

    def test_get_training_task_params_no_workflow(self):
        with self.assertRaises(AITrainingRequestError):
            ai_worker_api.get_training_task_params("invalid_uuid")

    @mock.patch.object(AITrainingWorkflow.objects, 'get')
    def test_get_training_task_params_database_error(self, mock_get):
        mock_get.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AITrainingInternalError):
            ai_worker_api.get_training_task_params(self.workflow_uuid)

    def test_create_classifiers(self):
        ai_worker_api.create_classifiers(self.workflow_uuid, CLASSIFIERS)

        # Expect that the workflow was marked complete
        workflow = AITrainingWorkflow.objects.get(uuid=self.workflow_uuid)
        self.assertIsNot(workflow.completed_at, None)

        # Expect that the classifier set was created with the correct data
        self.assertIsNot(workflow.classifier_set, None)
        saved_classifiers = workflow.classifier_set.classifiers_dict
        self.assertItemsEqual(CLASSIFIERS, saved_classifiers)

    def test_create_classifiers_no_workflow(self):
        with self.assertRaises(AITrainingRequestError):
            ai_worker_api.create_classifiers("invalid_uuid", CLASSIFIERS)

    @mock.patch.object(AITrainingWorkflow.objects, 'get')
    def test_create_classifiers_database_error(self, mock_get):
        mock_get.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AITrainingInternalError):
            ai_worker_api.create_classifiers(self.workflow_uuid, CLASSIFIERS)

    def test_create_classifiers_serialize_error(self):
        # Mutate the classifier data so it is NOT JSON-serializable
        classifiers = copy.deepcopy(CLASSIFIERS)
        classifiers[u"vøȼȺƀᵾłȺɍɏ"] = datetime.datetime.now()

        # Expect an error when we try to create the classifiers
        with self.assertRaises(AITrainingInternalError):
            ai_worker_api.create_classifiers(self.workflow_uuid, classifiers)

    def test_create_classifiers_missing_criteria(self):
        # Remove a criterion from the classifiers dict
        classifiers = copy.deepcopy(CLASSIFIERS)
        del classifiers[u"vøȼȺƀᵾłȺɍɏ"]

        # Expect an error when we try to create the classifiers
        with self.assertRaises(AITrainingRequestError):
            ai_worker_api.create_classifiers(self.workflow_uuid, classifiers)

    def test_create_classifiers_unrecognized_criterion(self):
        # Add an extra criterion to the classifiers dict
        classifiers = copy.deepcopy(CLASSIFIERS)
        classifiers[u"extra_criterion"] = copy.deepcopy(classifiers[u"vøȼȺƀᵾłȺɍɏ"])

        # Expect an error when we try to create the classifiers
        with self.assertRaises(AITrainingRequestError):
            ai_worker_api.create_classifiers(self.workflow_uuid, classifiers)

    @mock.patch.object(AIClassifier, 'classifier_data')
    def test_create_classifiers_upload_error(self, mock_data):
        # Simulate an error occurring when uploading the trained classifier
        mock_data.save.side_effect = IOError("OH NO!!!")
        with self.assertRaises(AITrainingInternalError):
            ai_worker_api.create_classifiers(self.workflow_uuid, CLASSIFIERS)

    def test_create_classifiers_twice(self):
        # Simulate repeated task execution for the same workflow
        # Since these are executed sequentially, the second call should
        # have no effect.
        ai_worker_api.create_classifiers(self.workflow_uuid, CLASSIFIERS)
        ai_worker_api.create_classifiers(self.workflow_uuid, CLASSIFIERS)

        # Expect that the workflow was marked complete
        workflow = AITrainingWorkflow.objects.get(uuid=self.workflow_uuid)
        self.assertIsNot(workflow.completed_at, None)

        # Expect that the classifier set was created with the correct data
        self.assertIsNot(workflow.classifier_set, None)
        saved_classifiers = workflow.classifier_set.classifiers_dict
        self.assertItemsEqual(CLASSIFIERS, saved_classifiers)

    def test_create_classifiers_no_training_examples(self):
        # Create a workflow with no training examples
        workflow = AITrainingWorkflow.objects.create(algorithm_id=ALGORITHM_ID)

        # Expect an error when we try to create classifiers
        with self.assertRaises(AITrainingInternalError):
            ai_worker_api.create_classifiers(workflow.uuid, CLASSIFIERS)


class AIWorkerGradingTest(CacheResetTest):
    """
    Tests for the AI API calls a worker would make when
    completing a grading task.
    """

    SCORES = {
        u"vøȼȺƀᵾłȺɍɏ": 1,
        u"ﻭɼค๓๓คɼ": 0
    }

    def setUp(self):
        """
        Create a grading workflow in the database.
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
            CLASSIFIERS, rubric, ALGORITHM_ID, STUDENT_ITEM.get('course_id'), STUDENT_ITEM.get('item_id')
        )
        workflow.classifier_set = classifier_set
        workflow.save()

    def test_get_grading_task_params(self):
        params = ai_worker_api.get_grading_task_params(self.workflow_uuid)
        expected_params = {
            'essay_text': ANSWER,
            'classifier_set': CLASSIFIERS,
            'algorithm_id': ALGORITHM_ID,
            'course_id': STUDENT_ITEM.get('course_id'),
            'item_id': STUDENT_ITEM.get('item_id')
        }
        self.assertItemsEqual(params, expected_params)

    def test_get_grading_task_params_no_workflow(self):
        with self.assertRaises(AIGradingRequestError):
            ai_worker_api.get_grading_task_params("invalid_uuid")

    def test_get_grading_task_params_no_classifiers(self):
        # Remove the classifiers from the workflow
        workflow = AIGradingWorkflow.objects.get(uuid=self.workflow_uuid)
        workflow.classifier_set = None
        workflow.save()

        # Should get an error when retrieving task params
        with self.assertRaises(AIGradingInternalError):
            ai_worker_api.get_grading_task_params(self.workflow_uuid)

    @mock.patch.object(AIGradingWorkflow.objects, 'get')
    def test_get_grading_task_params_database_error(self, mock_call):
        mock_call.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AIGradingInternalError):
            ai_worker_api.get_grading_task_params(self.submission_uuid)

    def test_invalid_classifier_data(self):
        # Modify the classifier data so it is not valid JSON
        invalid_json = "{"
        for classifier in AIClassifier.objects.all():
            classifier.classifier_data.save(uuid4().hex, ContentFile(invalid_json))

        # Should get an error when retrieving task params
        with self.assertRaises(AIGradingInternalError):
            ai_worker_api.get_grading_task_params(self.workflow_uuid)

    def test_create_assessment(self):
        ai_worker_api.create_assessment(self.workflow_uuid, self.SCORES)
        assessment = Assessment.objects.get(submission_uuid=self.submission_uuid)
        self.assertEqual(assessment.points_earned, 1)

    def test_create_assessment_no_workflow(self):
        with self.assertRaises(AIGradingRequestError):
            ai_worker_api.create_assessment("invalid_uuid", self.SCORES)

    def test_create_assessment_workflow_already_complete(self):
        # Try to create assessments for the same workflow multiple times
        ai_worker_api.create_assessment(self.workflow_uuid, self.SCORES)
        ai_worker_api.create_assessment(self.workflow_uuid, self.SCORES)

        # Expect that only one assessment is created for the submission
        num_assessments = Assessment.objects.filter(submission_uuid=self.submission_uuid).count()
        self.assertEqual(num_assessments, 1)

    @mock.patch.object(AIGradingWorkflow.objects, 'get')
    def test_create_assessment_database_error_retrieving_workflow(self, mock_call):
        mock_call.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AIGradingInternalError):
            ai_worker_api.create_assessment(self.workflow_uuid, self.SCORES)

    @mock.patch.object(Assessment.objects, 'create')
    def test_create_assessment_database_error_complete_workflow(self, mock_call):
        mock_call.side_effect = DatabaseError("KABOOM!")
        with self.assertRaises(AIGradingInternalError):
            ai_worker_api.create_assessment(self.workflow_uuid, self.SCORES)
