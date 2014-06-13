"""
"""
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from .algorithm import AIAlgorithm


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
        vectorizer = TfidfVectorizer(min_df=1, ngram_range=(1, 2), stop_words='english')
        transformed = vectorizer.fit_transform(
            [example.text for example in examples],
        )
        classifier = LinearSVC()
        classifier.fit(transformed, [example.score for example in examples])
        return {
            'vectorizer': pickle.dumps(vectorizer),
            'classifier': pickle.dumps(classifier)
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
        transformed = cache.get('transformed')
        if transformed is None:
            vectorizer = pickle.loads(classifier['vectorizer'])
            transformed = vectorizer.transform([text])
            cache['transformed'] = transformed

        classifier_obj = cache.get('classifier')
        if classifier_obj is None:
            classifier_obj = pickle.loads(classifier['classifier'])
            cache['classifier'] = classifier_obj

        return classifier_obj.predict(transformed)[0]
