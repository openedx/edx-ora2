"""
Define the ML algorithms used to train text classifiers.
"""
from abc import ABCMeta, abstractmethod
from collections import namedtuple
import importlib
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
        msg = u"Could not find algorithm \"u{}\" in the configuration.".format(algorithm_id)
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
            JSON-serializable: The trained classifier.  This MUST be JSON-serializable;
                if any of the classifier data is binary, it should be base-64 encoded.

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
            except (ImportError, AttributeError):
                raise AlgorithmLoadError(algorithm_id, cls_path)
