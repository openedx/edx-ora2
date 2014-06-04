# -*- coding: utf-8 -*-
"""
Tests for assessment models.
"""

from openassessment.test_utils import CacheResetTest
from openassessment.assessment.models import (
    Rubric, Criterion, CriterionOption, InvalidOptionSelection
)


class TestRubricOptionIds(CacheResetTest):
    """
    Test selection of options from a rubric.
    """

    NUM_CRITERIA = 4
    NUM_OPTIONS = 3

    def setUp(self):
        """
        Create a rubric in the database.
        """
        self.rubric = Rubric.objects.create()
        self.criteria = [
            Criterion.objects.create(
                rubric=self.rubric,
                name="test criterion {num}".format(num=num),
                order_num=num,
            ) for num in range(self.NUM_CRITERIA)
        ]

        self.options = dict()
        for criterion in self.criteria:
            self.options[criterion.name] = [
                CriterionOption.objects.create(
                    criterion=criterion,
                    name="test option {num}".format(num=num),
                    order_num=num,
                    points=num
                ) for num in range(self.NUM_OPTIONS)
            ]

    def test_option_ids(self):
        options_ids = self.rubric.options_ids({
            "test criterion 0": "test option 0",
            "test criterion 1": "test option 1",
            "test criterion 2": "test option 2",
            "test criterion 3": "test option 0",
        })
        self.assertEqual(options_ids, set([
            self.options['test criterion 0'][0].id,
            self.options['test criterion 1'][1].id,
            self.options['test criterion 2'][2].id,
            self.options['test criterion 3'][0].id
        ]))

    def test_option_ids_different_order(self):
        options_ids = self.rubric.options_ids({
            "test criterion 0": "test option 0",
            "test criterion 1": "test option 1",
            "test criterion 2": "test option 2",
            "test criterion 3": "test option 0",
        })
        self.assertEqual(options_ids, set([
            self.options['test criterion 0'][0].id,
            self.options['test criterion 1'][1].id,
            self.options['test criterion 2'][2].id,
            self.options['test criterion 3'][0].id
        ]))

    def test_option_ids_missing_criteria(self):
        with self.assertRaises(InvalidOptionSelection):
            self.rubric.options_ids({
                "test criterion 0": "test option 0",
                "test criterion 1": "test option 1",
                "test criterion 3": "test option 2",
            })

    def test_option_ids_extra_criteria(self):
        with self.assertRaises(InvalidOptionSelection):
            self.rubric.options_ids({
                "test criterion 0": "test option 0",
                "test criterion 1": "test option 1",
                "test criterion 2": "test option 2",
                "test criterion 3": "test option 1",
                "extra criterion": "test",
            })

    def test_option_ids_mutated_criterion_name(self):
        with self.assertRaises(InvalidOptionSelection):
            self.rubric.options_ids({
                "test mutated criterion": "test option 1",
                "test criterion 1": "test option 1",
                "test criterion 2": "test option 2",
                "test criterion 3": "test option 1",
            })

    def test_option_ids_mutated_option_name(self):
        with self.assertRaises(InvalidOptionSelection):
            self.rubric.options_ids({
                "test criterion 0": "test option 1",
                "test criterion 1": "test mutated option",
                "test criterion 2": "test option 2",
                "test criterion 3": "test option 1",
            })

    def test_options_ids_points(self):
        options_ids = self.rubric.options_ids_for_points({
            'test criterion 0': 0,
            'test criterion 1': 1,
            'test criterion 2': 2,
            'test criterion 3': 1
        })
        self.assertEqual(options_ids, set([
            self.options['test criterion 0'][0].id,
            self.options['test criterion 1'][1].id,
            self.options['test criterion 2'][2].id,
            self.options['test criterion 3'][1].id
        ]))

    def test_options_ids_points_caching(self):
        # First call: the dict is not cached
        with self.assertNumQueries(1):
            options_ids = self.rubric.options_ids_for_points({
                'test criterion 0': 0,
                'test criterion 1': 1,
                'test criterion 2': 2,
                'test criterion 3': 1
            })

        # Second call: the dict is not cached
        with self.assertNumQueries(0):
            options_ids = self.rubric.options_ids_for_points({
                'test criterion 0': 1,
                'test criterion 1': 2,
                'test criterion 2': 1,
                'test criterion 3': 0
            })

    def test_options_ids_first_of_duplicate_points(self):
        # Change the first criterion options so that the second and third
        # option have the same point value
        self.options['test criterion 0'][1].points = 5
        self.options['test criterion 0'][1].save()
        self.options['test criterion 0'][2].points = 5
        self.options['test criterion 0'][2].save()

        # Should get the first option back
        options_ids = self.rubric.options_ids_for_points({
            'test criterion 0': 5,
            'test criterion 1': 1,
            'test criterion 2': 2,
            'test criterion 3': 1
        })
        self.assertIn(self.options['test criterion 0'][1].id, options_ids)

    def test_options_ids_points_invalid_selection(self):
        with self.assertRaises(InvalidOptionSelection):
            self.rubric.options_ids_for_points({
                'test criterion 0': self.NUM_OPTIONS + 1,
                'test criterion 1': 2,
                'test criterion 2': 1,
                'test criterion 3': 0
            })
