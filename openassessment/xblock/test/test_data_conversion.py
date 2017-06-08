# -*- coding: utf-8 -*-
"""
Test OpenAssessment XBlock data_conversion.
"""

import ddt
import mock

from django.test import TestCase

from openassessment.xblock.data_conversion import (
    create_prompts_list, create_submission_dict, prepare_submission_for_serialization, update_assessments_format
)


@ddt.ddt
class DataConversionTest(TestCase):

    @ddt.data(
        (None, [{'description': ''}]),
        ('Test prompt.', [{'description': 'Test prompt.'}]),
        ('[{"description": "Test prompt."}]', [{'description': 'Test prompt.'}]),
    )
    @ddt.unpack
    def test_create_prompts_list(self, input, output):
        self.assertEqual(create_prompts_list(input), output)

    @ddt.data(
        (
            {'answer': {'text': 'a'}},
            [{'description': '1'}],
            {'answer': {'parts': [{'prompt': {'description': '1'}, 'text': 'a'}]}}
        ),
        (
            {'answer': {'parts': [{'text': 'a'}]}},
            [{'description': '1'}],
            {'answer': {'parts': [{'prompt': {'description': '1'}, 'text': 'a'}]}}
        ),
        (
            {'answer': {'parts': [{'text': 'a'}]}},
            [{'description': '1'}, {'description': '2'}],
            {'answer': {'parts': [{'prompt': {'description': '1'}, 'text': 'a'},
                                  {'prompt': {'description': '2'}, 'text': ''}]}}
        )
    )
    @ddt.unpack
    def test_create_submission_dict(self, input_submission, input_prompts, output):
        self.assertEqual(create_submission_dict(input_submission, input_prompts), output)

    @ddt.data(
        ([''], {'parts': [{'text': ''}]}),
        (['a', 'b'], {'parts': [{'text': 'a'}, {'text': 'b'}]})
    )
    @ddt.unpack
    def test_prepare_submission_for_serialization(self, input, output):
        self.assertEqual(prepare_submission_for_serialization(input), output)

    @ddt.data(
        ([{'answer': 'Ans'}], [{'answer': {'parts': [{'text': 'Ans'}]}}]),
    )
    @ddt.unpack
    def test_update_assessments_format(self, input, output):
        self.assertEqual(update_assessments_format([{
            'examples': input,
        }]), [{
            'examples': output,
        }])
