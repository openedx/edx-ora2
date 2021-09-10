"""
Test OpenAssessment XBlock data_conversion.
"""

import ddt

import mock
from django.test import TestCase

from openassessment.xblock.data_conversion import (
    create_prompts_list, create_submission_dict,
    list_to_conversational_format,
    prepare_submission_for_serialization,
    update_assessments_format,
    _verify_assessment_data,
    verify_assessment_parameters,
    verify_multiple_assessment_parameters
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


@ddt.ddt
class VerifyAssessmentData(TestCase):
    """
    Tests for assessment data verification functions and view wrappers
    """
    def dummy_translate(self, msg):
        """ Dummy version of the _ translation method that just returns the passed string """
        return msg

    def test_verify_assessment_data__not_dict(self):
        """
        Test for behavior when _verify_assessment is called with a non-dict parameter
        """
        result = _verify_assessment_data(self.dummy_translate, ['this', 'is', 'a', 'list'])
        self.assertIsNotNone(result)
        self.assertEqual("Assessment data must be a dictionary/object", result)

    @ddt.data(
        ('options_selected', 'You must provide options selected'),
        ('overall_feedback', 'You must provide overall feedback'),
        ('criterion_feedback', 'You must provide feedback for criteria')
    )
    @ddt.unpack
    def test_verify_assessment_data__missing_key_errors(self, key_to_remove, expected_message):
        """
        Test for behavior when _verify_assessment is called with a dict missing one of the required keys
        """
        base_assessment_data = {'options_selected': 1, 'overall_feedback': 2, 'criterion_feedback': 3}
        self.assertIsNone(_verify_assessment_data(self.dummy_translate, base_assessment_data))

        del base_assessment_data[key_to_remove]
        result = _verify_assessment_data(self.dummy_translate, base_assessment_data)
        self.assertIsNotNone(result)
        self.assertIn(expected_message, result)

    @ddt.data(None, "There was an error")
    @mock.patch('openassessment.xblock.data_conversion._verify_assessment_data')
    def test_verify_assessment_parameters(self, mock_verify_return_value, patched_verify):
        """
        Tests for behavior of verify_assessment_parameters
        """
        patched_verify.return_value = mock_verify_return_value
        mock_function = mock.Mock()
        instance, data, suffix = mock.Mock(), mock.Mock(), mock.Mock()

        result = verify_assessment_parameters(mock_function)(instance, data, suffix)
        if mock_verify_return_value is None:
            self.assertEqual(mock_function.return_value, result)
            mock_function.assert_called_once_with(instance, data, suffix)
        else:
            self.assertDictEqual({'success': False, 'msg': mock_verify_return_value}, result)
            mock_function.assert_not_called()

    @ddt.data(
        [None, None, None],
        [None, "There was an error", None],
        ["A", "B", "C"],
        ["A", "B", None],
    )
    @mock.patch('openassessment.xblock.data_conversion._verify_assessment_data')
    def test_verify_multiple_assessment_parameters(self, mock_verify_return_values, patched_verify):
        """
        Test for behavior of verify_multiple_assessment_parameters
        """
        patched_verify.side_effect = mock_verify_return_values
        mock_function = mock.Mock()
        instance, suffix = mock.Mock(), mock.Mock()
        data = [mock.Mock(), mock.Mock(), mock.Mock()]

        result = verify_multiple_assessment_parameters(mock_function)(instance, data, suffix)
        if not any(mock_verify_return_values):
            self.assertEqual(mock_function.return_value, result)
            mock_function.assert_called_once_with(instance, data, suffix)
        else:
            expected_errors = {
                i: error_msg
                for i, error_msg in enumerate(mock_verify_return_values)
                if error_msg is not None
            }
            self.assertDictEqual(
                result,
                {
                    'success': False,
                    'msg': "One or more of the submitted assessments is missing required fields",
                    'errors': expected_errors
                }
            )

    def test_verify_multiple_assessment_parameters__not_list(self):
        """
        Test for error behavior when verify_multiple_assessment_parameters is called with a parameter that
        is not a list
        """
        mock_function = mock.Mock()
        instance, suffix = mock.Mock(), mock.Mock()
        instance._ = self.dummy_translate
        data = "This string is not a list"
        result = verify_multiple_assessment_parameters(mock_function)(instance, data, suffix)
        self.assertDictEqual(
            {'success': False, 'msg': 'This view takes only a list as a parameter'},
            result
        )
        mock_function.assert_not_called()
