# coding=utf-8
"""
Test AI Django models.
"""
import copy
import ddt
from django.test import TestCase

from django.test.utils import override_settings
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.models import (
    AIClassifierSet, AIClassifier, AIGradingWorkflow, AI_CLASSIFIER_STORAGE,
    CLASSIFIERS_CACHE_IN_MEM, essay_text_from_submission
)
from openassessment.assessment.serializers import rubric_from_dict
from .constants import RUBRIC


CLASSIFIERS_DICT = {
    u"vøȼȺƀᵾłȺɍɏ": "test data",
    u"ﻭɼค๓๓คɼ": "more test data"
}
COURSE_ID = u"†3ß† çøU®ß3"
ITEM_ID = u"fake_item_id"


@ddt.ddt
class DataConversionTest(TestCase):

    @ddt.data(
        (u'Answer', u'Answer'),
        ({'answer': {'text': u'Answer'}}, u'Answer'),
        ({'answer': {'parts': [{'text': u'Answer 1'}, {'text': u'Answer 2'}]}}, u'Answer 1\nAnswer 2')
    )
    @ddt.unpack
    def test_essay_text_from_submission(self, input, output):
        self.assertEqual(essay_text_from_submission(input), output)


class AIClassifierTest(CacheResetTest):
    """
    Tests for the AIClassifier model.
    """

    def test_upload_to_path_default(self):
        # No path prefix provided in the settings
        classifier = self._create_classifier()
        components = classifier.classifier_data.name.split(u'/')
        self.assertEqual(len(components), 2)
        self.assertEqual(components[0], AI_CLASSIFIER_STORAGE)
        self.assertGreater(len(components[1]), 0)

    @override_settings(ORA2_FILE_PREFIX=u"ƒιℓє_ρяєƒιχ")
    def test_upload_to_path_with_prefix(self):
        classifier = self._create_classifier()
        components = classifier.classifier_data.name.split(u'/')
        self.assertEqual(len(components), 3)
        self.assertEqual(components[0], u"ƒιℓє_ρяєƒιχ")
        self.assertEqual(components[1], AI_CLASSIFIER_STORAGE)
        self.assertGreater(len(components[2]), 0)

    def _create_classifier(self):
        """
        Create and return an AIClassifier.
        """
        rubric = rubric_from_dict(RUBRIC)
        classifier_set = AIClassifierSet.create_classifier_set(
            CLASSIFIERS_DICT, rubric, "test_algorithm", COURSE_ID, ITEM_ID
        )
        return AIClassifier.objects.filter(classifier_set=classifier_set)[0]


class AIClassifierSetTest(CacheResetTest):
    """
    Tests for the AIClassifierSet model.
    """
    def setUp(self):
        super(AIClassifierSetTest, self).setUp()
        rubric = rubric_from_dict(RUBRIC)
        self.classifier_set = AIClassifierSet.create_classifier_set(
            CLASSIFIERS_DICT, rubric, "test_algorithm", COURSE_ID, ITEM_ID
        )

    def test_cache_downloads(self):
        # Retrieve the classifier dict twice, which should hit the caching code.
        # We can check that we're using the cache by asserting that
        # the number of database queries decreases.
        with self.assertNumQueries(1):
            first = self.classifier_set.classifier_data_by_criterion

        with self.assertNumQueries(0):
            second = self.classifier_set.classifier_data_by_criterion

        # Verify that we got the same value both times
        self.assertEqual(first, second)

    def test_file_cache_downloads(self):
        # Retrieve the classifiers dict, which should be cached
        # both in memory and on the file system
        first = self.classifier_set.classifier_data_by_criterion

        # Clear the in-memory cache
        # This simulates what happens when a worker process dies
        # after exceeding the maximum number of retries.
        CLASSIFIERS_CACHE_IN_MEM.clear()

        # We should still be able to retrieve the classifiers dict
        # from the on-disk cache, even if memory has been cleared
        with self.assertNumQueries(0):
            second = self.classifier_set.classifier_data_by_criterion

        # Verify that we got the correct classifiers dict back
        self.assertEqual(first, second)


class AIGradingWorkflowTest(CacheResetTest):
    """
    Tests for the AIGradingWorkflow model.
    """
    CLASSIFIERS_DICT = {
        u"vøȼȺƀᵾłȺɍɏ": "test data",
        u"ﻭɼค๓๓คɼ": "more test data"
    }
    COURSE_ID = u"test"
    ITEM_ID = u"test"
    ALGORITHM_ID = "test"

    def setUp(self):
        """
        Create a new grading workflow.
        """
        self.rubric = rubric_from_dict(RUBRIC)
        self.workflow = AIGradingWorkflow.objects.create(
            submission_uuid='test', essay_text='test',
            rubric=self.rubric, algorithm_id=self.ALGORITHM_ID,
            item_id=self.ITEM_ID, course_id=self.COURSE_ID
        )

        # Create a rubric with a similar structure, but different prompt
        similar_rubric_dict = copy.deepcopy(RUBRIC)
        similar_rubric_dict['prompts'] = [{"description": 'Different prompt!'}]
        self.similar_rubric = rubric_from_dict(similar_rubric_dict)

    def test_assign_most_recent_classifier_set(self):
        # No classifier sets are available
        found = self.workflow.assign_most_recent_classifier_set()
        self.assertFalse(found)
        self.assertIs(self.workflow.classifier_set, None)

        # Same rubric (exact), but different course id
        classifier_set = AIClassifierSet.create_classifier_set(
            self.CLASSIFIERS_DICT, self.rubric, self.ALGORITHM_ID,
            "different course!", self.ITEM_ID
        )
        found = self.workflow.assign_most_recent_classifier_set()
        self.assertTrue(found)
        self.assertEqual(classifier_set.pk, self.workflow.classifier_set.pk)

        # Same rubric (exact) but different item id
        classifier_set = AIClassifierSet.create_classifier_set(
            self.CLASSIFIERS_DICT, self.rubric, self.ALGORITHM_ID,
            self.COURSE_ID, "different item!"
        )
        found = self.workflow.assign_most_recent_classifier_set()
        self.assertTrue(found)
        self.assertEqual(classifier_set.pk, self.workflow.classifier_set.pk)

        # Same rubric (exact), but different algorithm id
        # Shouldn't change, since the algorithm ID doesn't match
        AIClassifierSet.create_classifier_set(
            self.CLASSIFIERS_DICT, self.rubric, "different algorithm!",
            self.COURSE_ID, self.ITEM_ID
        )
        found = self.workflow.assign_most_recent_classifier_set()
        self.assertTrue(found)
        self.assertEqual(classifier_set.pk, self.workflow.classifier_set.pk)

        # Same rubric *structure*, but in a different item
        # Shouldn't change, since the rubric isn't an exact match.
        AIClassifierSet.create_classifier_set(
            self.CLASSIFIERS_DICT, self.similar_rubric, self.ALGORITHM_ID,
            self.COURSE_ID, "different item!"
        )
        found = self.workflow.assign_most_recent_classifier_set()
        self.assertTrue(found)
        self.assertEqual(classifier_set.pk, self.workflow.classifier_set.pk)

        # Same rubric *structure* AND in the same course/item
        # This should replace our current classifier set
        classifier_set = AIClassifierSet.create_classifier_set(
            self.CLASSIFIERS_DICT, self.similar_rubric, self.ALGORITHM_ID,
            self.COURSE_ID, self.ITEM_ID
        )
        found = self.workflow.assign_most_recent_classifier_set()
        self.assertTrue(found)
        self.assertEqual(classifier_set.pk, self.workflow.classifier_set.pk)

        # Same rubric and same course/item
        # This is the ideal, so we should always prefer it
        classifier_set = AIClassifierSet.create_classifier_set(
            self.CLASSIFIERS_DICT, self.rubric, self.ALGORITHM_ID,
            self.COURSE_ID, self.ITEM_ID
        )
        found = self.workflow.assign_most_recent_classifier_set()
        self.assertTrue(found)
        self.assertEqual(classifier_set.pk, self.workflow.classifier_set.pk)
