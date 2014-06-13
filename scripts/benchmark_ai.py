#!/usr/bin/env python
"""
Benchmark the execution time of the EASE algorithm for scoring essays.
"""

import sys
import os
import json
import time
import math
import contextlib
from openassessment.assessment.worker.algorithm import AIAlgorithm, EaseAIAlgorithm, FakeAIAlgorithm
from openassessment.assessment.worker.classy import ClassyAlgorithm


NUM_TRIALS = 3
NUM_CRITERIA = 10
DATA_FILE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        'data/ai-test-data.json'
    )
)
NUM_TEST_SET = 20
#ALGORITHM = EaseAIAlgorithm
#ALGORITHM = FakeAIAlgorithm
ALGORITHM = ClassyAlgorithm

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
    print u"Loading training data from {path}...".format(path=data_path)
    with open(data_path) as data_file:
        input_examples = json.load(data_file)
    print "Done (loaded {num} examples)".format(num=len(input_examples))

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
    examples_by_criteria = {}
    for criterion_data in sys.argv[1:]:
        examples = load_training_data(criterion_data)
        examples_by_criteria[criterion_data] = examples
    algorithm = ALGORITHM()

    print "Training classifier..."
    with benchmark('Training'):
        classifiers = {}
        for criterion, examples in examples_by_criteria.iteritems():
            classifiers[criterion] = algorithm.train_classifier(examples[NUM_TEST_SET:])
    print "Done."

    print u"Scoring essays ({num} criteria)...".format(num=NUM_CRITERIA)
    num_correct = 0
    point_deltas = []
    total = 0
    for num in range(NUM_TRIALS):
        cache = {}
        for essay_num in range(NUM_TEST_SET):
            with benchmark('Scoring essay #{num}'.format(num=essay_num)):
                for criterion, examples in examples_by_criteria.iteritems():
                    example = examples[essay_num]
                    score = algorithm.score(example.text, classifiers[criterion], cache)
                    if score == example.score:
                        num_correct += 1
                    point_deltas.append(float(example.score) - float(score))
                    total += 1
        print "Finished scoring essay (trial #{num})".format(num=num)

    print u"Accuracy (correct): {correct} / {total} = {accuracy}".format(
        correct=num_correct,
        total=total,
        accuracy=(float(num_correct) / float(total))
    )

    error = float(sum([abs(delta) for delta in point_deltas])) / float(total)
    print u"Average error (points off per score): {error}".format(error=error)

    average = sum(point_deltas) / len(point_deltas)
    variance = sum([(average - delta) ** 2 for delta in point_deltas]) / len(point_deltas)
    stdev = math.sqrt(variance)
    print u"Stdev in error: {stdev}".format(stdev=stdev)


if __name__ == "__main__":
    main()
