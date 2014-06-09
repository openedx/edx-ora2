"""
Define the ML algorithms used to train text classifiers.
"""
from abc import ABCMeta, abstractmethod
from collections import namedtuple
import importlib
import traceback
import pickle
from django.conf import settings


class AIAlgorithmError(Exception):
    """
    An error occurred when using an AI algorithm.
    Superclass for more specific errors below.
    """
    pass


class UnknownAlgorithm(AIAlgorithmError):
    """
    Algorithm ID not found in the configuration.
    """
    def __init__(self, algorithm_id):
        msg = u"Could not find algorithm \"{}\" in the configuration.".format(algorithm_id)
        super(UnknownAlgorithm, self).__init__(msg)


class AlgorithmLoadError(AIAlgorithmError):
    """
    Unable to load the algorithm class.
    """
    def __init__(self, algorithm_id, algorithm_path):
        msg = (
            u"Could not load algorithm \"{algorithm_id}\" from \"{path}\""
        ).format(algorithm_id=algorithm_id, path=algorithm_path)
        super(AlgorithmLoadError, self).__init__(msg)


class TrainingError(AIAlgorithmError):
    """
    An error occurred while training a classifier from example essays.
    """
    pass


class ScoreError(AIAlgorithmError):
    """
    An error occurred while scoring an essay.
    """
    pass


class InvalidClassifier(ScoreError):
    """
    The classifier could not be used by this algorithm to score an essay.
    """
    pass


class AIAlgorithm(object):
    """
    Abstract base class for a supervised ML text classification algorithm.
    """
    __metaclass__ = ABCMeta

    # Example essay used as input to the training algorithm
    # `text` is a unicode string representing a student essay submission.
    # `score` is an integer score.
    # Note that `score` is used as an arbitrary label, so you could
    # have a set of examples with non-adjacent scores.
    ExampleEssay = namedtuple('ExampleEssay', ['text', 'score'])

    @abstractmethod
    def train_classifier(self, examples):
        """
        Train a classifier based on example essays and scores.

        Args:
            examples (list of AIAlgorithm.ExampleEssay): Example essays and scores.

        Returns:
            JSON-serializable: The trained classifier.  This MUST be JSON-serializable.

        Raises:
            TrainingError: The classifier could not be trained successfully.

        """
        pass

    @abstractmethod
    def score(self, text, classifier):
        """
        Score an essay using a classifier.

        Args:
            text (unicode): The text to classify.
            classifier (JSON-serializable): A classifier, using the same format
                as `train_classifier()`.

        Raises:
            InvalidClassifier: The provided classifier cannot be used by this algorithm.
            ScoreError: An error occurred while scoring.

        """
        pass

    @classmethod
    def algorithm_for_id(cls, algorithm_id):
        """
        Load an algorithm based on Django settings configuration.

        Args:
            algorithm_id (unicode): The identifier for the algorithm,
                which should be specified in Django settings.

        Returns:
            AIAlgorithm

        Raises:
             UnknownAlgorithm

        """
        algorithms = getattr(settings, "ORA2_AI_ALGORITHMS", dict())
        cls_path = algorithms.get(algorithm_id)

        if cls_path is None:
            raise UnknownAlgorithm(algorithm_id)
        else:
            module_path, _, name = cls_path.rpartition('.')
            try:
                algorithm_cls = getattr(importlib.import_module(module_path), name)
                return algorithm_cls()
            except (ImportError, ValueError, AttributeError):
                raise AlgorithmLoadError(algorithm_id, cls_path)


class FakeAIAlgorithm(AIAlgorithm):
    """
    Fake AI algorithm implementation that assigns scores randomly.
    We use this for testing the pipeline independently of EASE.
    """

    def train_classifier(self, examples):
        """
        Store the possible score labels, which will allow
        us to deterministically choose scores for other essays.
        """
        unique_sorted_scores = sorted(list(set(example.score for example in examples)))
        return {'scores': unique_sorted_scores}

    def score(self, text, classifier):
        """
        Choose a score for the essay deterministically based on its length.
        """
        if 'scores' not in classifier or len(classifier['scores']) == 0:
            raise InvalidClassifier("Classifier must provide score labels")
        else:
            score_index = len(text) % len(classifier['scores'])
            return classifier['scores'][score_index]


class EaseAIAlgorithm(AIAlgorithm):
    """
    Wrapper for the EASE library.
    See https://github.com/edx/ease for more information.

    Since EASE has many system dependencies, we don't include it explicitly
    in edx-ora2 requirements.  When testing locally, we use the fake
    algorithm implementation instead.
    """

    def train_classifier(self, examples):
        """
        Train a text classifier using the EASE library.
        The classifier is serialized as a dictionary with keys:
            * 'feature_extractor': The pickled feature extractor (transforms text into a numeric feature vector).
            * 'score_classifier': The pickled classifier (uses the feature vector to assign scores to essays).

        Because we are using `pickle`, the serialized classifiers are unfortunately
        tied to the particular version of ease/scikit-learn/numpy/scipy/nltk that we
        have installed at the time of training.

        Args:
            examples (list of AIAlgorithm.ExampleEssay): Example essays and scores.

        Returns:
            dict: The serializable classifier.

        Raises:
            TrainingError: The classifier could not be trained successfully.

        """
        feature_ext, classifier = self._train_classifiers(examples)
        return self._serialize_classifiers(feature_ext, classifier)

    def score(self, text, classifier):
        """
        Score essays using EASE.

        Args:
            text (unicode): The essay text to score.
            classifier (dict): The serialized classifiers created during training.

        Returns:
            int

        Raises:
            InvalidClassifier
            ScoreError

        """
        try:
            from ease.grade import grade    # pylint:disable=F0401
        except ImportError:
            msg = u"Could not import EASE to grade essays."
            raise ScoreError(msg)

        feature_extractor, score_classifier = self._deserialize_classifiers(classifier)

        grader_input = {
            'model': score_classifier,
            'extractor': feature_extractor,
            'prompt': ''
        }

        # EASE apparently can't handle non-ASCII unicode in the submission text
        # (although, oddly, training runs without error)
        # So we need to sanitize the input.
        sanitized_text = text.encode('ascii', 'ignore')

        try:
            results = grade(grader_input, sanitized_text)
        except:
            msg = (
                u"An unexpected error occurred while using "
                u"EASE to score an essay: {traceback}"
            ).format(traceback=traceback.format_exc())
            raise ScoreError(msg)

        if not results.get('success', False):
            msg = (
                u"Errors occurred while scoring an essay "
                u"using EASE: {errors}"
            ).format(errors=results.get('errors', []))
            raise ScoreError(msg)

        score = results.get('score')
        if score is None:
            msg = u"Error retrieving the score from EASE"
            raise ScoreError(msg)
        return score


    def _train_classifiers(self, examples):
        """
        Use EASE to train classifiers.

        Args:
            examples (list of AIAlgorithm.ExampleEssay): Example essays and scores.

        Returns:
            tuple of `feature_extractor` (an `ease.feature_extractor.FeatureExtractor` object)
            and `classifier` (a `sklearn.ensemble.GradientBoostingClassifier` object).

        Raises:
            TrainingError: Could not load EASE or could not complete training.

        """
        try:
            from ease.create import create  # pylint: disable=F0401
        except ImportError:
            msg = u"Could not import EASE to perform training."
            raise TrainingError(msg)

        input_essays = [example.text for example in examples]
        input_scores = [example.score for example in examples]

        try:
            # Train the classifiers
            # The third argument is the essay prompt, which EASE uses
            # to check if an input essay is too similar to the prompt.
            # Since we're not using this feature, we pass in an empty string.
            results = create(input_essays, input_scores, "")
        except:
            msg = (
                u"An unexpected error occurred while using "
                u"EASE to train classifiers: {traceback}"
            ).format(traceback=traceback.format_exc())
            raise TrainingError(msg)

        if not results.get('success', False):
            msg = (
                u"Errors occurred while training classifiers "
                u"using EASE: {errors}"
            ).format(errors=results.get('errors', []))
            raise TrainingError(msg)

        return results.get('feature_ext'), results.get('classifier')

    def _serialize_classifiers(self, feature_ext, classifier):
        """
        Serialize the classifier objects.

        Args:
            feature_extractor (ease.feature_extractor.FeatureExtractor)
            classifier (sklearn.ensemble.GradientBoostingClassifier)

        Returns:
            dict containing the pickled classifiers

        Raises:
            TrainingError: Could not serialize the classifiers.

        """
        try:
            return {
                'feature_extractor': pickle.dumps(feature_ext),
                'score_classifier': pickle.dumps(classifier),
            }
        except Exception as ex:
            msg = (
                u"An error occurred while serializing the classifiers "
                u"created by EASE: {ex}"
            ).format(ex=ex)
            raise TrainingError(msg)

    def _deserialize_classifiers(self, classifier_data):
        """
        Deserialize the classifier objects.

        Args:
            classifier_data (dict): The serialized classifiers.

        Returns:
            tuple of `(feature_extractor, score_classifier)`

        Raises:
            InvalidClassifier

        """
        if not isinstance(classifier_data, dict):
            raise InvalidClassifier("Classifier must be a dictionary.")

        try:
            feature_extractor = pickle.loads(classifier_data.get('feature_extractor'))
        except Exception as ex:
            msg = (
                u"An error occurred while deserializing the "
                u"EASE feature extractor: {ex}"
            ).format(ex=ex)
            raise InvalidClassifier(msg)

        try:
            score_classifier = pickle.loads(classifier_data.get('score_classifier'))
        except Exception as ex:
            msg = (
                u"An error occurred while deserializing the "
                u"EASE score classifier: {ex}"
            ).format(ex=ex)
            raise InvalidClassifier(msg)

        return feature_extractor, score_classifier
