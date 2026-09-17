"""
Test OpenAssessment XBlock data_conversion.
"""

import ddt

from django.test import TestCase

from openassessment.xblock.utils.data_conversion import (
    create_prompts_list, create_submission_dict,
    list_to_conversational_format,
    prepare_submission_for_serialization,
    update_assessments_format
)


@ddt.ddt
class DataConversionTest(TestCase):
    """ Test ora data conversions. """

    @ddt.data(
        (None, [{'description': ''}]),
        ('Test prompt.', [{'description': 'Test prompt.'}]),
        ('[{"description": "Test prompt."}]', [{'description': 'Test prompt.'}]),
    )
    @ddt.unpack
    def test_create_prompts_list(self, input_prompt, output):
        self.assertEqual(create_prompts_list(input_prompt), output)

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
        (None, ''),
        (['user'], 'user'),
        (['userA', 'userB'], 'userA and userB'),
        (['userA', 'userB', 'userC'], 'userA, userB, and userC'),
        (['A', 'B', 'C', 'D', 'E'], 'A, B, C, D, and E')
    )
    @ddt.unpack
    def test_list_to_conversational_format(self, input_list, output):
        self.assertEqual(list_to_conversational_format(input_list), output)

    @ddt.data(
        ([''], {'parts': [{'text': ''}]}),
        (['a', 'b'], {'parts': [{'text': 'a'}, {'text': 'b'}]})
    )
    @ddt.unpack
    def test_prepare_submission_for_serialization(self, input_prompt, output):
        self.assertEqual(prepare_submission_for_serialization(input_prompt), output)

    @ddt.data(
        ([{'answer': 'Ans'}], [{'answer': {'parts': [{'text': 'Ans'}]}}]),
        ([{'answer': ['Ans']}], [{'answer': {'parts': [{'text': 'Ans'}]}}]),
        ([{'answer': ['Ans', 'Ans1']}], [{'answer': {'parts': [{'text': 'Ans'}, {'text': 'Ans1'}]}}]),
        ([{'answer': []}], [{'answer': []}]),
    )
    @ddt.unpack
    def test_update_assessments_format(self, input_prompt, output):
        self.assertEqual(update_assessments_format([{
            'examples': input_prompt,
        }]), [{
            'examples': output,
        }])
