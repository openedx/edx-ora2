# coding=utf-8
"""
Tests for AI algorithm implementations.
"""
try:
    import cPickle as pickle
except ImportError:
    import pickle

import copy
import json
import base64
import datetime
import mock
from openassessment.test_utils import CacheResetTest
from openassessment.cache import FastCache, TempCache
from openassessment.assessment.worker.algorithm import (
    AIAlgorithm, FakeAIAlgorithm, TrainingError, InvalidClassifier
)
from openassessment.assessment.worker.ease_algorithm import EaseAIAlgorithm
from openassessment.assessment.worker.classy_algorithm import ClassyAIAlgorithm


EXAMPLES = [
    AIAlgorithm.ExampleEssay(u"Mine's a tale that can't be told, my ƒяєє∂σм I hold dear.", 2),
    AIAlgorithm.ExampleEssay(u"How years ago in days of old, when 𝒎𝒂𝒈𝒊𝒄 filled th air.", 1),
    AIAlgorithm.ExampleEssay(u"Ṫ'ẅäṡ in the darkest depths of Ṁöṛḋöṛ, I met a girl so fair.", 1),
    AIAlgorithm.ExampleEssay(u"But goﾚﾚuﾶ, and the evil one crept up and slipped away with her", 0),
    AIAlgorithm.ExampleEssay(u"", 4),
    AIAlgorithm.ExampleEssay(u".!?", 4),
    AIAlgorithm.ExampleEssay(u"no punctuation", 4),
    AIAlgorithm.ExampleEssay(u"one", 4),
]


INPUT_ESSAYS = [
    u"Good times, 𝑩𝒂𝒅 𝑻𝒊𝒎𝒆𝒔, you know I had my share",
    u"When my woman left home for a 𝒃𝒓𝒐𝒘𝒏 𝒆𝒚𝒆𝒅 𝒎𝒂𝒏",
    u"Well, I still don't seem to 𝒄𝒂𝒓𝒆",
    u"",
    u".!?",
    u"no punctuation",
    u"one",
]


class AIAlgorithmTest(CacheResetTest):
    """
    Base class for testing AI algorithm implementations.
    """
    ALGORITHM_CLASS = None

    def setUp(self):
        self.algorithm = self.ALGORITHM_CLASS()   # pylint:disable=E1102

    def _scores(self, classifier, input_essays):
        """
        Use the classifier to score multiple input essays.

        Args:
            input_essays (list of unicode): The essays to score.

        Returns:
            list of int: The scores

        """
        cache = FastCache()
        temp_cache = TempCache()
        return [
            self.algorithm.score(input_essay, classifier, cache, temp_cache)
            for input_essay in input_essays
        ]

    def _assert_valid_scores(self):
        """
        Assert that the algorithm produces valid and consistent scores.
        """
        classifier = self.algorithm.train_classifier(EXAMPLES)
        scores = self._scores(classifier, INPUT_ESSAYS)

        # Check that we got scores in the correct range
        valid_scores = set(example.score for example in EXAMPLES)
        for score in scores:
            self.assertIn(score, valid_scores)

        # Check that the scores are consistent when we re-run the algorithm
        repeat_scores = self._scores(classifier, INPUT_ESSAYS)
        self.assertEqual(scores, repeat_scores)

    def _assert_json_serializable(self):
        """
        Assert that trained classifiers are JSON-serializable.
        """
        classifier = self.algorithm.train_classifier(EXAMPLES)
        serialized = json.dumps(classifier)
        deserialized = json.loads(serialized)

        # This should not raise an exception
        scores = self._scores(deserialized, INPUT_ESSAYS)
        self.assertEqual(len(scores), len(INPUT_ESSAYS))

    def _assert_all_examples_same_score(self):
        """
        Assert that the algorithm raises an exception 
        for an unbalanced training set in which all examples have the same score.
        """
        examples = [
            AIAlgorithm.ExampleEssay(u"Test ëṡṡäÿ", 1),
            AIAlgorithm.ExampleEssay(u"Another test ëṡṡäÿ", 1),
        ]

        with self.assertRaises(TrainingError):
            self.algorithm.train_classifier(examples)

    def _assert_most_examples_same_score(self):
        """
        Assert that the algorithm handles an unbalanced training set.
        This can sometimes cause exceptions to be thrown
        during K-folds cross-validation if there are not positive/negative
        examples in each fold.
        """
        # All training examples have the same score except for one
        examples = [
            AIAlgorithm.ExampleEssay(u"Test ëṡṡäÿ", 1),
            AIAlgorithm.ExampleEssay(u"Another test ëṡṡäÿ", 1),
            AIAlgorithm.ExampleEssay(u"Different score", 0),
        ]
        classifier = self.algorithm.train_classifier(examples)
        scores = self._scores(classifier, INPUT_ESSAYS)

        # Check that we got scores back.
        # This is not a very rigorous assertion -- we're mainly
        # checking that we got this far without an exception.
        self.assertEqual(len(scores), len(INPUT_ESSAYS))

    def _assert_no_examples(self):
        """
        Assert that the algorithm raises an exception if no training
        examples are provided.
        """
        with self.assertRaises(TrainingError):
            self.algorithm.train_classifier([])


class FakeAIAlgorithmTest(AIAlgorithmTest):
    """
    Test for the fake AI algorithm implementation.
    """
    ALGORITHM_CLASS = FakeAIAlgorithm

    def test_train_and_score(self):
        classifier = self.algorithm.train_classifier(EXAMPLES)
        expected_scores = [2, 0, 0, 0, 4, 2, 4]
        scores = self._scores(classifier, INPUT_ESSAYS)
        self.assertEqual(scores, expected_scores)

    def test_score_classifier_missing_key(self):
        with self.assertRaises(InvalidClassifier):
            self.algorithm.score(u"Test input", {}, FastCache(), TempCache())

    def test_score_classifier_no_scores(self):
        with self.assertRaises(InvalidClassifier):
            self.algorithm.score(u"Test input", {'scores': []}, FastCache(), TempCache())


class EaseAIAlgorithmTest(AIAlgorithmTest):
    """
    Test for the EASE AI library wrapper.
    """
    ALGORITHM_CLASS = EaseAIAlgorithm

    def test_train_and_score(self):
        self._assert_valid_scores()

    def test_all_examples_have_same_score(self):
        self._assert_all_examples_same_score()

    def test_no_examples(self):
        self._assert_no_examples()

    def test_most_examples_have_same_score(self):
        self._assert_most_examples_same_score()

    def test_json_serializable(self):
        self._assert_json_serializable()

    def test_serialized_classifier_not_a_dict(self):
        with self.assertRaises(InvalidClassifier):
            self.algorithm.score(u"Test ëṡṡäÿ", "not a dict", FastCache(), TempCache())

    @mock.patch('openassessment.assessment.worker.ease_algorithm.pickle.dumps')
    def test_pickle_serialize_error(self, mock_call):
        mock_call.side_effect = pickle.PickleError("Test error!")
        with self.assertRaises(TrainingError):
            self.algorithm.train_classifier(EXAMPLES)

    @mock.patch('openassessment.assessment.worker.ease_algorithm.pickle.loads')
    def test_pickle_deserialize_feature_extractor_error(self, mock_call):
        mock_call.side_effect = pickle.PickleError("Test error!")
        classifier = self.algorithm.train_classifier(EXAMPLES)
        with self.assertRaises(InvalidClassifier):
            self.algorithm.score(u"Test ëṡṡäÿ", classifier, FastCache(), TempCache())

    @mock.patch('openassessment.assessment.worker.ease_algorithm.pickle.loads')
    def test_pickle_deserialize_classifier_error(self, mock_call):
        classifier = self.algorithm.train_classifier(EXAMPLES)
        # Raise an exception on the second call to `pickle.loads`
        mock_call.side_effect = [
            pickle.loads(base64.b64decode(classifier['feature_extractor'])),
            pickle.PickleError("Test error!")
        ]
        with self.assertRaises(InvalidClassifier):
            self.algorithm.score(u"Test ëṡṡäÿ", classifier, FastCache(), TempCache())


class ClassyAIAlgorithmTest(AIAlgorithmTest):
    """
    Tests for the "classy" AI algorithm.
    """
    ALGORITHM_CLASS = ClassyAIAlgorithm

    def test_train_and_score(self):
        self._assert_valid_scores()

    def test_all_examples_have_same_score(self):
        self._assert_all_examples_same_score()

    def test_most_examples_have_same_score(self):
        self._assert_most_examples_same_score()

    def test_json_serializable(self):
        self._assert_json_serializable()

    def test_most_examples_have_same_score(self):
        # All training examples have the same score except for one
        examples = [
            AIAlgorithm.ExampleEssay(u"Test ëṡṡäÿ", 1),
            AIAlgorithm.ExampleEssay(u"Another test ëṡṡäÿ", 1),
            AIAlgorithm.ExampleEssay(u"Different score", 0),
        ]
        classifier = self.algorithm.train_classifier(examples)
        scores = self._scores(classifier, INPUT_ESSAYS)

        # Check that we got scores back.
        # This is not a very rigorous assertion -- we're mainly
        # checking that we got this far without an exception.
        self.assertEqual(len(scores), len(INPUT_ESSAYS))

    def test_no_examples(self):
        self._assert_no_examples()

    def test_pickle_serialize_error(self):
        self.algorithm.pickle_dumps = mock.MagicMock(
            side_effect=pickle.PickleError("Test error!")
        )
        with self.assertRaises(TrainingError):
            self.algorithm.train_classifier(EXAMPLES)

    def test_pickle_deserialize_vectorizer_error(self):
        classifier = self.algorithm.train_classifier(EXAMPLES)
        self.algorithm.pickle_loads = mock.MagicMock(
            side_effect=pickle.PickleError("Test error!")
        )
        with self.assertRaises(InvalidClassifier):
            self.algorithm.score(u"Test ëṡṡäÿ", classifier, FastCache(), TempCache())

    def test_pickle_deserialize_classifier_error(self):
        classifier = self.algorithm.train_classifier(EXAMPLES)

        # Raise an exception on the second call to `pickle.loads`
        self.algorithm.pickle_loads = mock.MagicMock(
            side_effect= [
                pickle.loads(base64.b64decode(classifier['vectorizer'])),
                pickle.PickleError("Test error!")
            ]
        )
        with self.assertRaises(InvalidClassifier):
            self.algorithm.score(u"Test ëṡṡäÿ", classifier, FastCache(), TempCache())

    def test_deserialize_bad_data(self):
        classifier_data = self.algorithm.train_classifier(EXAMPLES)
        mutations = [None, 0.1, u"ëẍṗḷöḋë!", datetime.datetime.now()]
        mutations += [base64.b64encode(pickle.dumps(mutation)) for mutation in mutations]
        for key in ['vectorizer', 'classifier']:
            mutated_data = copy.deepcopy(classifier_data)
            for mutation in mutations:
                mutated_data[key] = mutation
                with self.assertRaises(InvalidClassifier):
                    self.algorithm.score(u"Test essay", mutated_data, FastCache(), TempCache())

    def test_deserialize_missing_keys(self):
        classifier_data = self.algorithm.train_classifier(EXAMPLES)
        for key in ['vectorizer', 'classifier']:
            mutated_data = copy.deepcopy(classifier_data)
            del mutated_data[key]
            with self.assertRaises(InvalidClassifier):
                self.algorithm.score(u"Test essay", mutated_data, FastCache(), TempCache())

    def test_serialized_classifier_not_a_dict(self):
        with self.assertRaises(InvalidClassifier):
            self.algorithm.score(u"Test ëṡṡäÿ", "not a dict", FastCache(), TempCache())
