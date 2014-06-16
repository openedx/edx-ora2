#!/usr/bin/env python
"""
Benchmark the execution time of the EASE algorithm for scoring essays.
"""

import sys
import json
import time
import math
import contextlib
import random
from collections import defaultdict
import csv
from openassessment.assessment.worker.algorithm import AIAlgorithm, EaseAIAlgorithm, FakeAIAlgorithm
from openassessment.assessment.worker.classy import ClassyAlgorithm


NUM_TRIALS = 10
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
        dictionary of with keys for each criterion
        and values that are lists of `AIAlgorithm.ExampleEssay`s

    Also returns the number of examples loaded.

    """
    print u"Loading training data from {path}...".format(path=data_path)
    with open(data_path) as data_file:
        input_examples = json.load(data_file)
    print "Done (loaded {num} examples)".format(num=len(input_examples))

    # Shuffle the input examples
    random.shuffle(input_examples)

    # Separate by criterion
    examples_by_criterion = defaultdict(list)
    for example in input_examples:
        for criterion, score in example['criteria'].iteritems():
            examples_by_criterion[criterion].append(
                AIAlgorithm.ExampleEssay(
                    text=example['text'],
                    score=int(score)
                )
            )
    return examples_by_criterion, len(input_examples)


def avg(nums):
    return sum([float(num) for num in nums]) / len(nums)


def stdev(nums):
    average = avg(nums)
    variance = sum([(average - float(num)) ** 2 for num in nums]) / len(nums)
    return math.sqrt(variance)


def write_output(output_file, num_examples, scoring_times, point_deltas_by_criterion):
    """
    Write the output data to a CSV file.
    """
    with open(output_file, 'w') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['Num trials', NUM_TRIALS])
        csv_writer.writerow(['Training set size', num_examples - NUM_TEST_SET])
        csv_writer.writerow(['Test set size', NUM_TEST_SET])

        csv_writer.writerow(['Avg time per essay (seconds)', avg(scoring_times)])
        csv_writer.writerow(['Stdev time per essay', stdev(scoring_times)])

        point_deltas = []
        for deltas in point_deltas_by_criterion.values():
            point_deltas.extend([abs(delta) for delta in deltas])
        csv_writer.writerow(['Avg error (points off per score)', avg(point_deltas)])
        csv_writer.writerow(['Stdev error', stdev(point_deltas)])

        for criterion, point_deltas in point_deltas_by_criterion.iteritems():
            abs_point_deltas = [abs(delta) for delta in point_deltas]
            csv_writer.writerow([u'{criterion} error'.format(criterion=criterion), avg(abs_point_deltas)])
            csv_writer.writerow([u'{criterion} stdev error'.format(criterion=criterion), stdev(abs_point_deltas)])


def main():
    """
    Time training/scoring using EASE.
    """
    if len(sys.argv) < 3:
        print "Usage: <INPUT EXAMPLES> <OUTPUT CSV>"
        sys.exit(1)

    point_deltas_by_criterion = defaultdict(list)
    score_matrix = defaultdict(lambda: defaultdict(lambda: 0))
    scores = defaultdict(lambda: 0)
    scoring_times = []

    for trial_num in range(NUM_TRIALS):
        print "Trial #{trial}".format(trial=trial_num)
        examples_by_criteria, num_examples = load_training_data(sys.argv[1])
        algorithm = ALGORITHM()

        print "Training classifiers..."
        with benchmark('Training'):
            classifiers = {}
            for criterion, examples in examples_by_criteria.iteritems():
                classifiers[criterion] = algorithm.train_classifier(examples[NUM_TEST_SET:])
        print "Done."

        print "Scoring essays..."
        for essay_num in range(NUM_TEST_SET):
            cache = {}
            with benchmark('Scoring essay #{num}'.format(num=essay_num), store=scoring_times):
                for criterion, examples in examples_by_criteria.iteritems():
                    example = examples[essay_num]
                    score = algorithm.score(example.text, classifiers[criterion], cache)
                    delta = float(example.score) - float(score)
                    point_deltas_by_criterion[criterion].append(delta)
                    score_matrix[score][example.score] += 1
                    scores[score] += 1

    print u"Writing output to {output}".format(output=sys.argv[2])
    write_output(sys.argv[2], num_examples, scoring_times, point_deltas_by_criterion)

    for actual_score, expected_score_counts in score_matrix.iteritems():
        print "Score given: {}".format(actual_score)
        for expected_score, count in expected_score_counts.iteritems():
            print "== Expected {expected} ({correctness}): {percent}%".format(
                expected=expected_score,
                percent=(float(count) / float(scores[actual_score])) * 100,
                correctness="correct" if actual_score == expected_score else "incorrect"
            )


if __name__ == "__main__":
    main()
