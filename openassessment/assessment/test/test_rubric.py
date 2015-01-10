# -*- coding: utf-8 -*-
"""
Tests for assessment models.
"""

import copy
from openassessment.test_utils import CacheResetTest
from openassessment.assessment.models import (
    Rubric, Criterion, CriterionOption, InvalidRubricSelection
)
from openassessment.assessment.test.constants import RUBRIC


class RubricIndexTest(CacheResetTest):
    """
    Test selection of options from a rubric.
    """

    NUM_CRITERIA = 4
    NUM_OPTIONS = 3

    def setUp(self):
        """
        Create a rubric in the database.
        """
        super(RubricIndexTest, self).setUp()

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

    def test_find_option(self):
        self.assertEqual(
            self.rubric.index.find_option("test criterion 0", "test option 0"),
            self.options["test criterion 0"][0]
        )
        self.assertEqual(
            self.rubric.index.find_option("test criterion 1", "test option 1"),
            self.options["test criterion 1"][1]
        )
        self.assertEqual(
            self.rubric.index.find_option("test criterion 2", "test option 2"),
            self.options["test criterion 2"][2]
        )
        self.assertEqual(
            self.rubric.index.find_option("test criterion 3", "test option 0"),
            self.options["test criterion 3"][0]
        )

    def test_find_missing_criteria(self):
        missing = self.rubric.index.find_missing_criteria([
            'test criterion 0', 'test criterion 1', 'test criterion 3'
        ])
        expected_missing = set(['test criterion 2'])
        self.assertEqual(missing, expected_missing)

    def test_invalid_option(self):
        with self.assertRaises(InvalidRubricSelection):
            self.rubric.index.find_option("test criterion 0", "invalid")

    def test_valid_option_wrong_criterion(self):
        # Add another option to the first criterion
        new_option = CriterionOption.objects.create(
            criterion=self.criteria[0],
            name="extra option",
            order_num=(self.NUM_OPTIONS + 1),
            points=4
        )

        # We should be able to find it in the first criterion
        self.assertEqual(
            new_option,
            self.rubric.index.find_option("test criterion 0", "extra option")
        )

        # ... but not from another criterion
        with self.assertRaises(InvalidRubricSelection):
            self.rubric.index.find_option("test criterion 1", "extra option")

    def test_find_option_for_points(self):
        self.assertEqual(
            self.rubric.index.find_option_for_points("test criterion 0", 0),
            self.options["test criterion 0"][0]
        )
        self.assertEqual(
            self.rubric.index.find_option_for_points("test criterion 1", 1),
            self.options["test criterion 1"][1]
        )
        self.assertEqual(
            self.rubric.index.find_option_for_points("test criterion 2", 2),
            self.options["test criterion 2"][2]
        )
        self.assertEqual(
            self.rubric.index.find_option_for_points("test criterion 3", 1),
            self.options["test criterion 3"][1]
        )

    def test_find_option_for_points_first_of_duplicate_points(self):
        # Change the first criterion options so that the second and third
        # option have the same point value
        self.options['test criterion 0'][1].points = 5
        self.options['test criterion 0'][1].save()
        self.options['test criterion 0'][2].points = 5
        self.options['test criterion 0'][2].save()

        # Should get the first option back
        option = self.rubric.index.find_option_for_points("test criterion 0", 5)
        self.assertEqual(option, self.options['test criterion 0'][1])

    def test_find_option_for_points_invalid_selection(self):
        # No such point value
        with self.assertRaises(InvalidRubricSelection):
            self.rubric.index.find_option_for_points("test criterion 0", 10)

        # No such criterion
        with self.assertRaises(InvalidRubricSelection):
            self.rubric.index.find_option_for_points("no such criterion", 0)

    def test_valid_points_wrong_criterion(self):
        # Add another option to the first criterion
        new_option = CriterionOption.objects.create(
            criterion=self.criteria[0],
            name="extra option",
            order_num=(self.NUM_OPTIONS + 1),
            points=10
        )

        # We should be able to find it in the first criterion
        self.assertEqual(
            new_option,
            self.rubric.index.find_option_for_points("test criterion 0", 10)
        )

        # ... but not from another criterion
        with self.assertRaises(InvalidRubricSelection):
            self.rubric.index.find_option_for_points("test criterion 1", 10)


class RubricHashTest(CacheResetTest):
    """
    Tests of the rubric content and structure hash.
    """
    def test_structure_hash_identical(self):
        first_hash = Rubric.structure_hash_from_dict(RUBRIC)

        # Same structure, but different text should have the same structure hash
        altered_rubric = copy.deepcopy(RUBRIC)
        altered_rubric['prompts'] = [{"description": 'altered!'}]
        for criterion in altered_rubric['criteria']:
            criterion['prompt'] = 'altered!'
            for option in criterion['options']:
                option['explanation'] = 'altered!'
        second_hash = Rubric.structure_hash_from_dict(altered_rubric)

        # Expect that the two hashes are the same
        self.assertEqual(first_hash, second_hash)

    def test_structure_hash_extra_keys(self):
        first_hash = Rubric.structure_hash_from_dict(RUBRIC)

        # Same structure, add some extra keys
        altered_rubric = copy.deepcopy(RUBRIC)
        altered_rubric['extra'] = 'extra!'
        altered_rubric['criteria'][0]['extra'] = 'extra!'
        altered_rubric['criteria'][0]['options'][0]['extra'] = 'extra!'
        second_hash = Rubric.structure_hash_from_dict(altered_rubric)

        # Expect that the two hashes are the same
        self.assertEqual(first_hash, second_hash)

    def test_structure_hash_criterion_order_changed(self):
        first_hash = Rubric.structure_hash_from_dict(RUBRIC)
        altered_rubric = copy.deepcopy(RUBRIC)
        altered_rubric['criteria'][0]['order_num'] = 5
        second_hash = Rubric.structure_hash_from_dict(altered_rubric)
        self.assertNotEqual(first_hash, second_hash)

    def test_structure_hash_criterion_name_changed(self):
        first_hash = Rubric.structure_hash_from_dict(RUBRIC)
        altered_rubric = copy.deepcopy(RUBRIC)
        altered_rubric['criteria'][0]['name'] = 'altered!'
        second_hash = Rubric.structure_hash_from_dict(altered_rubric)
        self.assertNotEqual(first_hash, second_hash)

    def test_structure_hash_option_order_changed(self):
        first_hash = Rubric.structure_hash_from_dict(RUBRIC)
        altered_rubric = copy.deepcopy(RUBRIC)
        altered_rubric['criteria'][0]['options'][0]['order_num'] = 5
        second_hash = Rubric.structure_hash_from_dict(altered_rubric)
        self.assertNotEqual(first_hash, second_hash)

    def test_structure_hash_option_name_changed(self):
        first_hash = Rubric.structure_hash_from_dict(RUBRIC)
        altered_rubric = copy.deepcopy(RUBRIC)
        altered_rubric['criteria'][0]['options'][0]['name'] = 'altered!'
        second_hash = Rubric.structure_hash_from_dict(altered_rubric)
        self.assertNotEqual(first_hash, second_hash)

    def test_structure_hash_option_points_changed(self):
        first_hash = Rubric.structure_hash_from_dict(RUBRIC)
        altered_rubric = copy.deepcopy(RUBRIC)
        altered_rubric['criteria'][0]['options'][0]['points'] = 'altered!'
        second_hash = Rubric.structure_hash_from_dict(altered_rubric)
        self.assertNotEqual(first_hash, second_hash)
