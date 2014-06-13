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
import random
from collections import defaultdict
from openassessment.assessment.worker.algorithm import AIAlgorithm, EaseAIAlgorithm, FakeAIAlgorithm
from openassessment.assessment.worker.classy import ClassyAlgorithm


NUM_TRIALS = 2
NUM_CRITERIA = 10
DATA_FILE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        'data/ai-test-data.json'
    )
)
NUM_TEST_SET = 10
#ALGORITHM = EaseAIAlgorithm
#ALGORITHM = FakeAIAlgorithm
ALGORITHM = ClassyAlgorithm

@contextlib.contextmanager
def benchmark(name, store=None):
    """
    Print the duration in seconds for a block of code.

    Args:
        name (unicode): A descriptive name for the benchmark

    Kwargs:
        store (list): If provided, append the time in seconds to this list.

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
    if store is not None:
        store.append(duration)


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


def stdev(nums):
    average = sum(nums) / len(nums)
    variance = sum([(average - num) ** 2 for num in nums]) / len(nums)
    return math.sqrt(variance)


def main():
    """
    Time training/scoring using EASE.
    """
    num_correct = 0
    point_deltas = []
    point_deltas_by_criterion = defaultdict(list)
    total = 0
    scoring_times = []

    for trial_num in range(NUM_TRIALS):
        print "Trial #{trial}".format(trial=trial_num)
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
        for essay_num in range(NUM_TEST_SET):
            cache = {}
            with benchmark('Scoring essay #{num}'.format(num=essay_num), store=scoring_times):
                for criterion, examples in examples_by_criteria.iteritems():
                    example = examples[essay_num]
                    score = algorithm.score(example.text, classifiers[criterion], cache)
                    if score == example.score:
                        num_correct += 1
                    delta = float(example.score) - float(score)
                    point_deltas.append(delta)
                    point_deltas_by_criterion[criterion].append(delta)
                    total += 1

    print u"Average time per essay (seconds): {time}".format(
        time=(sum(scoring_times) / len(scoring_times))
    )
    print u"Stdev time per essay: {stdev}".format(stdev=stdev(scoring_times))

    print u"Accuracy (correct): {correct} / {total} = {accuracy}".format(
        correct=num_correct,
        total=total,
        accuracy=(float(num_correct) / float(total))
    )

    error = float(sum([abs(delta) for delta in point_deltas])) / float(total)
    print u"Average error (points off per score): {error}".format(error=error)
    print u"Stdev in error: {stdev}".format(stdev=stdev(point_deltas))

    for criterion in examples_by_criteria.keys():
        crit_deltas = point_deltas_by_criterion[criterion]
        error = float(sum([abs(delta) for delta in crit_deltas])) / len(crit_deltas)
        print u"Criterion {criterion} average error (points off per score): {error}".format(criterion=criterion, error=error)
        print u"Criterion {criterion} stdev in error: {stdev}".format(criterion=criterion, stdev=stdev(crit_deltas))


if __name__ == "__main__":
    main()
