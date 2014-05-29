# coding=utf-8
"""
Test AI Django models.
"""
from django.test.utils import override_settings
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.models import (
    AIClassifierSet, AIClassifier, AI_CLASSIFIER_STORAGE
)
from openassessment.assessment.serializers import rubric_from_dict
from .constants import RUBRIC


class AIClassifierTest(CacheResetTest):
    """
    Tests for the AIClassifier model.
    """
    CLASSIFIERS_DICT = {
        u"vøȼȺƀᵾłȺɍɏ": "test data",
        u"ﻭɼค๓๓คɼ": "more test data"
    }

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
            self.CLASSIFIERS_DICT, rubric, "test_algorithm"
        )
        return AIClassifier.objects.filter(classifier_set=classifier_set)[0]
