"""
A basic scoring algorithm that uses scikit-learn and nltk.
"""
try:
    import cPickle as pickle
except ImportError:
    import pickle

import string   # pylint: disable=W0402
import base64
import hashlib
import warnings
import numpy
import nltk
import scipy
import sklearn
from sklearn.pipeline import FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.grid_search import GridSearchCV
from sklearn.svm import SVC
from .algorithm import AIAlgorithm, TrainingError, InvalidClassifier


WORD_PATTERNS = [
    (r'^-?[0-9]+(.[0-9]+)?$', 'CD'),
    (r'.*ould$', 'MD'),
    (r'.*ing$', 'VBG'),
    (r'.*ed$', 'VBD'),
    (r'.*ness$', 'NN'),
    (r'.*ment$', 'NN'),
    (r'.*ful$', 'JJ'),
    (r'.*ious$', 'JJ'),
    (r'.*ble$', 'JJ'),
    (r'.*ic$', 'JJ'),
    (r'.*ive$', 'JJ'),
    (r'.*ic$', 'JJ'),
    (r'.*est$', 'JJ'),
    (r'^a$', 'PREP'),
    (r'.*s$', 'NNS'),
]


# Table mapping each unicode punctuation code point
# to None (meaning it will be removed).
STRIP_PUNCTUATION_TABLE = {
    ord(char): None
    for char in string.punctuation
}

STEMMER = nltk.PorterStemmer()


from .data import COMMON_WORD_TAGS
DEFAULT_TAGGER = nltk.DefaultTagger('NN')
REGEX_TAGGER = nltk.tag.RegexpTagger(WORD_PATTERNS, backoff=DEFAULT_TAGGER)
COMMON_WORD_TAGGER = nltk.UnigramTagger(model=COMMON_WORD_TAGS, backoff=REGEX_TAGGER)
TAGGER = COMMON_WORD_TAGGER


def strip_punctuation(text):
    """
    Return the text without punctuation characters.

    Args:
        text (unicode)

    Returns:
        unicode

    """
    return text.translate(STRIP_PUNCTUATION_TABLE)


def tokenize_and_stem(text):
    """
    Tokenize and stem words.

    Args:
        text (unicode): The text to tokenize and stem.

    Yields:
        unicode: word stem

    """
    for word in nltk.word_tokenize(strip_punctuation(text)):
        yield STEMMER.stem(word)

    for char in text:
        if char in string.punctuation:
            yield char


def tokenize_and_tag_pos(text):
    """
    Tokenize words and tag parts of speech.

    Args:
        text (unicode): The text to tokenize and tag.

    Returns:
        list of Part-of-speech tokens

    """
    return [tagged[1] for tagged in TAGGER.tag(nltk.word_tokenize(text))]


class ClassyAIAlgorithm(AIAlgorithm):
    """
    A basic scoring algorithm that uses:
        * TF-IDF for text feature extraction (scikit-learn)
        * Stop-word removal for English (scikit-learn)
        * Word tokenization (nltk)
        * Regex part-of-speech tagging (nltk)
        * Support vector machine for supervised learning and classification (scikit-learn)

    The algorithm is designed to be fast (especially for grading) and accurate.

    """
    VERSION = "0.0.1"

    def __init__(self):
        """Initialize the classifier.  """
        # Make it easier for tests to inject mocks for `pickle` calls
        # Scikit also uses pickle internally, so this helps ensure
        # that we don't patch those calls.
        self.pickle_loads = pickle.loads
        self.pickle_dumps = pickle.dumps

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
        # Check that we have at least two unique scores
        if len(set(example.score for example in examples)) < 2:
            raise TrainingError("You must provide at least one positive and one negative training example")

        vectorizer = FeatureUnion([
            ('tfidf', TfidfVectorizer(
                tokenizer=tokenize_and_stem,
                min_df=1,
                ngram_range=(1, 2),
                stop_words='english'
            )),
            ('pos', CountVectorizer(
                preprocessor=strip_punctuation,
                tokenizer=tokenize_and_tag_pos,
                ngram_range=(1, 3)
            )),
        ])
        classifier = SVC()

        input_features = [example.text for example in examples]
        targets = [example.score for example in examples]
        features = vectorizer.fit_transform(input_features)

        params = {'C': [10.0 ** power for power in range(-2, 5)]}

        # Perform a grid search to find the SVM parameter
        # that minimizes training error.
        try:
            grid_search = GridSearchCV(classifier, param_grid=params)

            # Suppress warnings about unbalanced training sets
            # when performing cross-validation.
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                grid_search.fit(features, numpy.array(targets))

            best_estimator = grid_search.best_estimator_
        except ValueError:
            # This can happen if we don't have enough positive/negative
            # examples to run cross-validation.
            # If so, we just use the default parameter values.
            classifier.fit(features, numpy.array(targets))
            best_estimator = classifier

        try:
            return {
                'vectorizer': base64.b64encode(self.pickle_dumps(vectorizer)),
                'classifier': base64.b64encode(self.pickle_dumps(best_estimator)),
                'algorithm-version': self.VERSION,
                'sklearn-version': sklearn.__version__,
                'nltk-version': nltk.__version__,
                'numpy-version': numpy.__version__,
                'scipy-version': scipy.__version__,
            }
        except (pickle.PickleError, ValueError, TypeError) as ex:
            msg = (
                u"An error occurred while serializing the classifier data: {ex}"
            ).format(ex=ex)
            raise TrainingError(msg)

    def score(self, text, classifier_data, cache, temp_cache):
        """
        Score an essay using a classifier.

        Args:
            text (unicode): The text to classify.
            classifier_data (JSON-serializable): A classifier, using the same format
                as `train_classifier()`.
            cache (openassessment.cache.FastCache): An in-memory cache that persists between tasks.
            temp_cache (openassessment.cache.TempCache): An in-memory cache that persists
                for the duration of the current task.

        Raises:
            InvalidClassifier: The provided classifier cannot be used by this algorithm.
            ScoreError: An error occurred while scoring.

        """
        if not isinstance(classifier_data, dict):
            raise InvalidClassifier(
                u"Classifier data should be a dict, not {type}".format(type=type(classifier_data))
            )

        missing_keys = set(['classifier', 'vectorizer']) - set(classifier_data.keys())
        if len(missing_keys) > 0:
            msg = (
                u"Classifier data dict is missing key(s): {missing}"
            ).format(missing=", ".join(missing_keys))
            raise InvalidClassifier(msg)

        features = temp_cache.get(text)
        if features is None:
            vectorizer = self._deserialize_vectorizer(classifier_data['vectorizer'], cache)
            features = vectorizer.transform([text])
            temp_cache.set(text, features)
        classifier = self._deserialize_classifier(classifier_data['classifier'], cache)

        return classifier.predict(features)[0]

    def _deserialize_vectorizer(self, vectorizer_data, cache):
        """
        Deserialize the vectorizer from the classifier data.

        Args:
            vectorizer_data (basestring): The vectorizer data from the training step.
            cache (openassessment.cache.FastCache): An in-memory cache.

        Returns:
            sklearn.pipeline.FeatureUnion

        Raises:
            InvalidClassifier

        """
        if not isinstance(vectorizer_data, str):
            if isinstance(vectorizer_data, unicode):
                vectorizer_data = vectorizer_data.encode('utf-8')
            else:
                msg = u"Serialized classifier must be a string, not {type}".format(
                    type=type(vectorizer_data)
                )
                raise InvalidClassifier(msg)

        vectorizer_cache_key = self._cache_key('vectorizer', vectorizer_data)
        vectorizer = cache.get(vectorizer_cache_key)
        if vectorizer is None:
            try:
                vectorizer = self.pickle_loads(base64.b64decode(vectorizer_data))
            except (pickle.PickleError, ValueError, TypeError, EOFError) as ex:
                msg = (
                    u"An error occurred while deserializing the vectorizer: {ex}"
                ).format(ex=ex)
                raise InvalidClassifier(msg)
            if not isinstance(vectorizer, FeatureUnion):
                msg = (
                    u"Vectorizer in classifier data must be of type "
                    u"sklearn.pipeline.FeatureUnion, not {type}"
                ).format(type=type(vectorizer))
                raise InvalidClassifier(msg)
            cache.set(vectorizer_cache_key, vectorizer)
        return vectorizer

    def _deserialize_classifier(self, classifier_data, cache):
        """
        Deserialize the classifier from the classifier data.

        Args:
            classifier_data (basestring): The classifier data from the training step.
            cache (openassessment.cache.FastCache): An in-memory cache.

        Returns:
            sklearn.svc.SVC

        Raises:
            InvalidClassifier

        """
        if not isinstance(classifier_data, str):
            if isinstance(classifier_data, unicode):
                classifier_data = classifier_data.encode('utf-8')
            else:
                msg = u"Serialized classifier must be a bytestring, not {type}".format(
                    type=type(classifier_data)
                )
                raise InvalidClassifier(msg)

        classifier_cache_key = self._cache_key('classifier', classifier_data)
        classifier = cache.get(classifier_cache_key)
        if classifier is None:
            try:
                classifier = self.pickle_loads(base64.b64decode(classifier_data))
            except (pickle.PickleError, ValueError, TypeError, EOFError) as ex:
                msg = (
                    u"An error occurred while deserializing the classifier: {ex}"
                ).format(ex=ex)
                raise InvalidClassifier(msg)
            if not isinstance(classifier, SVC):
                msg = (
                    u"Classifier in classifier data must be of type "
                    u"sklearn.svc.SVC, not {type}"
                ).format(type=type(classifier))
                raise InvalidClassifier(msg)
            cache.set(classifier_cache_key, classifier)
        return classifier

    def _cache_key(self, name, contents):
        """
        Return a cache key using an MD5 hash digest of `contents`.

        Args:
            name (unicode or str): The name of the key.
            contents (str): Used to create a hash digest for the key.
        """
        hasher = hashlib.md5()
        if isinstance(contents, unicode):
            contents = contents.encode('utf-8')
        hasher.update(contents)
        return u"ora2.ai.algorithm.classy.{name}.{hash}".format(name=name, hash=hasher.hexdigest())
