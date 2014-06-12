#!/usr/bin/env python
"""
Benchmark the execution time of the EASE algorithm for scoring essays.
"""

import os
import json
import time
import contextlib
from openassessment.assessment.worker.algorithm import AIAlgorithm, EaseAIAlgorithm


NUM_TRIALS = 3
NUM_CRITERIA = 10
DATA_FILE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        'data/ai-test-data.json'
    )
)

@contextlib.contextmanager
def benchmark(name):
    """
    Print the duration in seconds for a block of code.

    Args:
        name (unicode): A descriptive name for the benchmark

    Returns:
        None

    Yields:
        None

    """
    start = time.clock()
    yield
    end = time.clock()
    duration = end - start
    print u"{name} took {duration} seconds".format(name=name, duration=duration)


def load_training_data(data_path):
    """
    Load the example essays and scores.

    Args:
        data_path (unicode): The path to the JSON data file.
        This should be a serialized list of dictionaries
        with keys 'text' (unicode) and 'score' (int).

    Returns:
        list of `AIAlgorithm.ExampleEssay`s

    """
    print "Loading training data..."
    with open(data_path) as data_file:
        input_examples = json.load(data_file)
    print "Done."

    return [
        AIAlgorithm.ExampleEssay(
            text=example['text'],
            score=int(example['score'])
        )
        for example in input_examples
    ]


def main():
    """
    Time training/scoring using EASE.
    """
    examples = load_training_data(DATA_FILE_PATH)
    algorithm = EaseAIAlgorithm()

    print "Training classifier..."
    with benchmark('Training'):
        classifier = algorithm.train_classifier(examples[:-1])
    print "Done."

    print u"Scoring essays ({num} criteria)...".format(num=NUM_CRITERIA)
    for num in range(NUM_TRIALS):
        cache = {}
        with benchmark('Scoring (rubric)'):
            for _ in range(NUM_CRITERIA):
                with benchmark('Scoring (criteria)'):
                    algorithm.score(examples[-1].text, classifier, cache)
        print "Finished scoring essay #{num}".format(num=num)


if __name__ == "__main__":
    main()
