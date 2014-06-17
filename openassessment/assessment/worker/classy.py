"""
"""
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.svm import SVC
from sklearn.pipeline import FeatureUnion
import nltk
from .algorithm import AIAlgorithm


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
    (r'.*', 'NN')
]


def tokenizer(text):
    tagger = nltk.tag.RegexpTagger(WORD_PATTERNS)
    return [
        tagged[1] if tagged[1] is not None else '?'
        for tagged in tagger.tag(nltk.word_tokenize(text))
    ]


def stemmer(text):
    stemmer = nltk.PorterStemmer()
    return [stemmer.stem(token) for token in nltk.word_tokenize(text)]


class ClassyAlgorithm(AIAlgorithm):
    """
    A super-classy text classification algorithm :)
    """

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
        pipeline = FeatureUnion([
            ('tfid', TfidfVectorizer(
                tokenizer=stemmer,
                min_df=1,
                ngram_range=(1, 2),
                stop_words='english'
            )),
            ('pos', CountVectorizer(tokenizer=tokenizer, ngram_range=(1, 2)))
        ])
        transformed = pipeline.fit_transform([example.text for example in examples])
        scores = [example.score for example in examples]
        classifier = SVC()
        classifier.fit(transformed, scores)
        return {
            'pipeline': pickle.dumps(pipeline),
            'classifier': pickle.dumps(classifier),
            'min_score': min(scores)
        }

    def score(self, text, classifier, cache):
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
        # Pre-checks
        if len(text.strip()) < 300:
            return classifier['min_score']

        transformed = cache.get('transformed')
        if transformed is None:
            vectorizer = pickle.loads(classifier['pipeline'])
            transformed = vectorizer.transform([text])
            cache['transformed'] = transformed

        classifier_obj = cache.get('classifier')
        if classifier_obj is None:
            classifier_obj = pickle.loads(classifier['classifier'])
            cache['classifier'] = classifier_obj

        return classifier_obj.predict(transformed)[0]
