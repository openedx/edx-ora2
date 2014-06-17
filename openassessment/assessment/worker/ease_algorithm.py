"""
Wrapper for the EASE library.
See https://github.com/edx/ease for more information.
"""
try:
    import cPickle as pickle
except ImportError:
    import pickle

import traceback
import hashlib
import base64
import numpy
import nltk
import scipy
import sklearn
from ease.essay_set import EssaySet
from ease.create import create
from .algorithm import AIAlgorithm, TrainingError, ScoreError, InvalidClassifier


class EaseAIAlgorithm(AIAlgorithm):
    """
    Wrapper for the EASE library.
    See https://github.com/edx/ease for more information.

    Since EASE has many system dependencies, we don't include it explicitly
    in edx-ora2 requirements.  When testing locally, we use the fake
    algorithm implementation instead.
    """
    VERSION = "0.0.1"

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
        # Check that we have at least two unique scores
        if len(set(example.score for example in examples)) < 2:
            raise TrainingError("You must provide at least one positive and one negative training example")

        feature_ext, classifier = self._train_classifiers(examples)
        return self._serialize_classifiers(feature_ext, classifier)

    def score(self, text, classifier, cache, temp_cache):
        """
        Score essays using EASE.

        Args:
            text (unicode): The essay text to score.
            classifier (dict): The serialized classifiers created during training.
            cache (openassessment.cache.FastCache): An in-memory cache that persists between tasks.
            temp_cache (openassessment.cache.TempCache): An in-memory cache that persists
                for the duration of the current task.

        Returns:
            int

        Raises:
            InvalidClassifier
            ScoreError

        """
        feature_extractor, score_classifier = self._deserialize_classifiers(classifier, cache)

        # The following is a modified version of `ease.grade.grade()`,
        # skipping things we don't use (cross-validation, feedback)
        # and caching essay sets across criteria.  This allows us to
        # avoid some expensive NLTK operations, particularly tagging
        # parts of speech.
        try:
            # Get the essay set from the cache or create it.
            # Since all essays to be graded are assigned a dummy
            # score of "0", we can safely re-use the essay set
            # for each criterion in the rubric.
            # EASE can't handle non-ASCII unicode, so we need
            # to strip out non-ASCII chars.
            essay_set = temp_cache.get(text)
            if essay_set is None:
                essay_set = EssaySet(essaytype="test")
                essay_set.add_essay(text.encode('ascii', 'ignore'), 0)
                temp_cache.set(text, essay_set)

            # Extract features from the text
            features = feature_extractor.gen_feats(essay_set)

            # Predict a score
            return int(score_classifier.predict(features)[0])
        except:
            msg = (
                u"An unexpected error occurred while using "
                u"EASE to score an essay: {traceback}"
            ).format(traceback=traceback.format_exc())
            raise ScoreError(msg)

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
                'feature_extractor': base64.b64encode(pickle.dumps(feature_ext)),
                'score_classifier': base64.b64encode(pickle.dumps(classifier)),
                'algorithm-version': self.VERSION,
                'sklearn-version': sklearn.__version__,
                'nltk-version': nltk.__version__,
                'numpy-version': numpy.__version__,
                'scipy-version': scipy.__version__,
            }
        except (pickle.PickleError, ValueError, TypeError) as ex:
            msg = (
                u"An error occurred while serializing the classifiers "
                u"created by EASE: {ex}"
            ).format(ex=ex)
            raise TrainingError(msg)

    def _deserialize_classifiers(self, classifier_data, cache):
        """
        Deserialize the classifier objects.

        Args:
            classifier_data (dict): The serialized classifiers.
            cache (Django cache): An in-memory cache.

        Returns:
            tuple of `(feature_extractor, score_classifier)`

        Raises:
            InvalidClassifier

        """
        if not isinstance(classifier_data, dict):
            raise InvalidClassifier("Classifier must be a dictionary.")

        serialized_extractor = classifier_data['feature_extractor']
        cache_key = self._cache_key('feature-extractor', serialized_extractor)
        feature_extractor = cache.get(cache_key)
        if feature_extractor is None:
            try:
                feature_extractor = pickle.loads(base64.b64decode(serialized_extractor))
            except (pickle.PickleError, ValueError, TypeError) as ex:
                msg = (
                    u"An error occurred while deserializing the "
                    u"EASE feature extractor: {ex}"
                ).format(ex=ex)
                raise InvalidClassifier(msg)
            else:
                cache.set(cache_key, feature_extractor)

        serialized_classifier = classifier_data['score_classifier']
        cache_key = self._cache_key('score-classifier', serialized_classifier)
        score_classifier = cache.get(cache_key)
        if score_classifier is None:
            try:
                score_classifier = pickle.loads(base64.b64decode(serialized_classifier))
            except (pickle.PickleError, ValueError, TypeError) as ex:
                msg = (
                    u"An error occurred while deserializing the "
                    u"EASE score classifier: {ex}"
                ).format(ex=ex)
                raise InvalidClassifier(msg)
            else:
                cache.set(cache_key, score_classifier)

        return feature_extractor, score_classifier

    def _cache_key(self, name, contents):
        """
        Return a cache key using an MD5 hash digest of `contents`.

        Args:
            name (str): The name of the key.
            contents (str): Used to create a hash digest for the key.
        """
        hasher = hashlib.md5()
        if isinstance(contents, unicode):
            contents = contents.encode('utf-8')
        hasher.update(contents)
        return u"ora2.ai.algorithm.ease.{name}.{hash}".format(name=name, hash=hasher.hexdigest())
