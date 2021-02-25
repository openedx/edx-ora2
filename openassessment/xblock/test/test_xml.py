"""
Tests for serializing to/from XML.
"""
import copy
import json
from unittest import mock

import dateutil.parser
import ddt
import pytz

from django.test import TestCase

import lxml.etree as etree
from openassessment.xblock.data_conversion import create_prompts_list
from openassessment.xblock.openassessmentblock import OpenAssessmentBlock
from openassessment.xblock.xml import (UpdateFromXmlError, _parse_prompts_xml, parse_assessments_xml,
                                       parse_examples_xml, parse_from_xml_str, parse_rubric_xml,
                                       serialize_assessments_to_xml_str, serialize_content,
                                       serialize_examples_to_xml_str, serialize_rubric_to_xml_str)


def _parse_date(value):
    """
    Parse test-data date into a TZ-aware datetime.

    Args:
        value (string or None): The value to parse.

    Returns:
        TZ-aware datetime or None.
    """
    if value is None:
        return value
    return dateutil.parser.parse(value).replace(tzinfo=pytz.utc)


@ddt.ddt
class TestSerializeContent(TestCase):
    """
    Test serialization of OpenAssessment XBlock content to XML.
    """
    BASIC_CRITERIA = [
        {
            "order_num": 0,
            "label": "Test criterion",
            "name": "Test criterion",
            "prompt": "Test criterion prompt",
            "feedback": "disabled",
            "options": [
                {
                    "order_num": 0,
                    "points": 0,
                    "label": "Maybe",
                    "name": "Maybe",
                    "explanation": "Maybe explanation"
                }
            ]
        }
    ]

    BASIC_PROMPTS = [
        [
            {
                "description": "Prompt 1."
            },
            {
                "description": "Prompt 2."
            }
        ]
    ]

    BASIC_ASSESSMENTS = [
        {
            "name": "student-training",
            "start": "2014-02-27T09:46:28.873926",
            "due": "2014-05-30T00:00:00.92926",
            "examples": [
                {
                    "answer": "ẗëṡẗ äṅṡẅëṛ",
                    "options_selected": [
                        {
                            "criterion": "Test criterion",
                            "option": "Maybe"
                        }
                    ]
                }
            ]
        },
        {
            "name": "peer-assessment",
            "start": "2014-02-27T09:46:28.873926",
            "due": "2014-05-30T00:00:00.92926",
            "must_grade": 5,
            "must_be_graded_by": 3,
        },
        {
            "name": "self-assessment",
            "start": '2014-04-01T00:00:00.000000',
            "due": "2014-06-01T00:00:00.92926",
        },
        {
            "name": "staff-assessment",
            "required": False,
        },
    ]

    def setUp(self):
        """
        Mock the OA XBlock.
        """
        super().setUp()
        self.oa_block = mock.MagicMock(OpenAssessmentBlock)

    def _configure_xblock(self, data):
        """ Helper method of xblock configuration for tests. """
        self.oa_block.title = data.get('title', '')
        self.oa_block.text_response = data.get('text_response', '')
        self.oa_block.text_response_editor = data.get('text_response_editor', 'text')
        self.oa_block.file_upload_response = data.get('file_upload_response', None)
        self.oa_block.prompt = data.get('prompt')
        self.oa_block.prompts = create_prompts_list(data.get('prompt'))
        self.oa_block.prompts_type = data.get('prompts_type', 'text')
        self.oa_block.rubric_feedback_prompt = data.get('rubric_feedback_prompt')
        self.oa_block.rubric_feedback_default_text = data.get('rubric_feedback_default_text')
        self.oa_block.start = _parse_date(data.get('start'))
        self.oa_block.due = _parse_date(data.get('due'))
        self.oa_block.submission_start = data.get('submission_start')
        self.oa_block.submission_due = data.get('submission_due')
        self.oa_block.rubric_criteria = data.get('criteria', copy.deepcopy(self.BASIC_CRITERIA))
        self.oa_block.rubric_assessments = data.get('assessments', copy.deepcopy(self.BASIC_ASSESSMENTS))

        self.oa_block.file_upload_type = data.get('file_upload_type')
        self.oa_block.white_listed_file_types = data.get('white_listed_file_types')
        self.oa_block.allow_multiple_files = data.get('allow_multiple_files')
        self.oa_block.allow_latex = data.get('allow_latex')
        self.oa_block.leaderboard_show = data.get('leaderboard_show', 0)
        self.oa_block.group_access = json.loads(data.get('group_access', "{}"))

        self.oa_block.teams_enabled = data.get('teams_enabled', None)
        self.oa_block.selected_teamset_id = data.get('selected_teamset_id', None)
        self.oa_block.show_rubric_during_response = data.get('show_rubric_during_response')

    @ddt.file_data('data/serialize.json')
    def test_serialize(self, data):
        self._configure_xblock(data)
        xml = serialize_content(self.oa_block)

        # Compare the XML with our expected output
        # To make the comparison robust, first parse the actual and expected XML
        # then compare elements/attributes in the tree.
        try:
            parsed_actual = etree.fromstring(xml)
        except (ValueError, etree.XMLSyntaxError):
            self.fail(f"Could not parse output XML:\n{xml}")

        # Assume that the test data XML is valid; if not, this will raise an error
        # instead of a test failure.
        parsed_expected = etree.fromstring("".join(data['expected_xml']))

        # Pretty-print and reparse the expected XML
        pretty_expected = etree.tostring(parsed_expected, pretty_print=True, encoding='unicode')
        parsed_expected = etree.fromstring(pretty_expected)

        # Walk both trees, comparing elements and attributes
        actual_elements = list(parsed_actual.getiterator())
        expected_elements = list(parsed_expected.getiterator())
        self.assertEqual(
            len(actual_elements), len(expected_elements),
            msg=f"Incorrect XML output:\nActual: {xml}\nExpected: {pretty_expected}"
        )

        for actual, expected in zip(actual_elements, expected_elements):
            self.assertEqual(actual.tag, expected.tag)
            self.assertEqual(
                actual.text, expected.text,
                msg="Incorrect text for {tag}.  Expected '{expected}' but found '{actual}'".format(
                    tag=actual.tag, expected=expected.text, actual=actual.text
                )
            )
            self.assertCountEqual(
                list(actual.items()), list(expected.items()),
                msg="Incorrect attributes for {tag}.  Expected {expected} but found {actual}".format(
                    tag=actual.tag, expected=list(expected.items()), actual=list(actual.items())
                )
            )

    @ddt.file_data('data/serialize.json')
    def test_serialize_rubric(self, data):
        self._configure_xblock(data)
        xml_str = serialize_rubric_to_xml_str(self.oa_block)
        self.assertIn("<rubric>", xml_str)
        if data.get('prompt'):
            self.assertNotIn(data['prompt'], xml_str)

    @ddt.file_data('data/serialize.json')
    def test_serialize_examples(self, data):
        self._configure_xblock(data)
        for assessment in data['assessments']:
            if assessment['name'] == 'student-training' and assessment['examples']:
                xml_str = serialize_examples_to_xml_str(assessment)
                for part in assessment['examples'][0]['answer']['parts']:
                    self.assertIn(part['text'], xml_str)

    @ddt.file_data('data/serialize.json')
    def test_serialize_assessments(self, data):
        self._configure_xblock(data)
        xml_str = serialize_assessments_to_xml_str(self.oa_block)
        self.assertIn(data['assessments'][0]['name'], xml_str)

    def test_mutated_criteria_dict(self):
        self._configure_xblock({})

        # We have to be really permissive with the data we'll accept.
        # If the data we're retrieving is somehow corrupted,
        # Studio authors should still be able to retrive an XML representation
        # so they can edit and fix the issue.
        # To test this, we systematically mutate a valid rubric dictionary by
        # mutating the dictionary, then asserting that we can parse the generated XML.
        for criteria_dict in self.BASIC_CRITERIA:
            for mutated_dict in self._dict_mutations(criteria_dict):
                self.oa_block.rubric_criteria = mutated_dict
                xml = serialize_content(self.oa_block)

                try:
                    etree.fromstring(xml)
                except Exception as ex:     # pylint:disable=W0703
                    msg = f"Could not parse mutated criteria dict {mutated_dict}\n{ex}"
                    self.fail(msg)

    def test_mutated_prompts_dict(self):
        self._configure_xblock({})

        for prompts_list in self.BASIC_PROMPTS:
            for mutated_list in self._list_mutations(prompts_list):
                self.oa_block.prompts = mutated_list
                xml = serialize_content(self.oa_block)

                try:
                    etree.fromstring(xml)
                except Exception as ex:  # pylint:disable=W0703
                    msg = f"Could not parse mutated prompts list {mutated_list}\n{ex}"
                    self.fail(msg)

    def test_mutated_assessments_dict(self):
        self._configure_xblock({})

        for assessment_dict in self.BASIC_ASSESSMENTS:
            for mutated_dict in self._dict_mutations(assessment_dict):
                self.oa_block.rubric_assessments = [mutated_dict]
                xml = serialize_content(self.oa_block)

                try:
                    etree.fromstring(xml)
                except Exception as ex:     # pylint:disable=W0703
                    msg = "Could not parse mutated assessment dict {assessment}\n{ex}".format(
                        assessment=mutated_dict, ex=ex
                    )
                    self.fail(msg)

    @ddt.data("title", "prompt", "start", "due", "submission_due", "submission_start", "leaderboard_show")
    def test_mutated_field(self, field):
        self._configure_xblock({})

        for mutated_value in [0, "\u9282", None]:
            setattr(self.oa_block, field, mutated_value)
            xml = serialize_content(self.oa_block)

            try:
                etree.fromstring(xml)
            except Exception as ex:     # pylint:disable=W0703
                msg = "Could not parse mutated field {field} with value {value}\n{ex}".format(
                    field=field, value=mutated_value, ex=ex
                )
                self.fail(msg)

    def test_serialize_missing_names_and_labels(self):
        # Configure rubric criteria and options with no names or labels
        # This *should* never happen, but if it does, recover gracefully
        # by assigning unique names and empty labels
        self._configure_xblock({})

        for criterion in self.oa_block.rubric_criteria:
            del criterion['name']
            del criterion['label']
            for option in criterion['options']:
                del option['name']
                del option['label']

        xml = serialize_content(self.oa_block)
        content_dict = parse_from_xml_str(xml)

        # Verify that all names are unique
        # and that all labels are empty
        criterion_names = set()
        option_names = set()
        criteria_count = 0
        options_count = 0
        for criterion in content_dict['rubric_criteria']:
            criterion_names.add(criterion['name'])
            self.assertEqual(criterion['label'], '')
            criteria_count += 1

            for option in criterion['options']:
                option_names.add(option['name'])
                self.assertEqual(option['label'], '')
                options_count += 1

        self.assertEqual(len(criterion_names), criteria_count)
        self.assertEqual(len(option_names), options_count)

    def _dict_mutations(self, input_dict):
        """
        Iterator over mutations of a dictionary:
        1) Remove keys
        2) Empty lists/dictionaries
        3) Change value to None
        4) Change value to unicode
        5) Change value to an integer

        Args:
            input_dict (dict): A JSON-serializable dictionary to traverse.

        Yields:
            dict
        """
        for key, val in input_dict.items():

            # Mutation #1: Remove the key
            print(f"== Removing key {key}")
            yield {k: v for k, v in input_dict.items() if k != key}

            if isinstance(val, dict):

                # Mutation #2: Empty dict
                print(f"== Emptying dict {key}")
                yield self._mutate_dict(input_dict, key, dict())

                # Mutation #3-5: value mutations
                yield from self._value_mutations(input_dict, key)

                # Recursively mutate sub keys
                for sub_mutation in self._dict_mutations(val):
                    yield self._mutate_dict(input_dict, key, sub_mutation)

            elif isinstance(val, list):
                # Mutation #2: Empty list
                print(f"== Emptying list {key}")
                yield self._mutate_dict(input_dict, key, list())

                # Mutation #3-5: value mutations
                yield from self._value_mutations(input_dict, key)

                # Recursively mutate sub-items
                for item in val:
                    if isinstance(item, dict):
                        for sub_mutation in self._dict_mutations(item):
                            yield self._mutate_dict(input_dict, key, sub_mutation)

            else:
                # Mutation #3-5: value mutations
                yield from self._value_mutations(input_dict, key)

    def _list_mutations(self, input_list):
        """
        Iterator over mutations of a list:
        1) Empty list
        2) Replace list with None
        3) Replace list with unicode
        4) Replace list with an integer

        Args:
            input_list (list): A JSON-serializable list to traverse.

        Yields:
            list
        """
        print("== Emptying list")
        yield list()

        # Mutation #3-5: value mutations
        yield from (None, "\u9731", 0)

        # Recursively mutate sub-items
        for index, item in enumerate(input_list):
            if isinstance(item, dict):
                for sub_mutation in self._dict_mutations(item):
                    yield self._mutate_list(input_list, index, sub_mutation)

    def _value_mutations(self, input_dict, key):
        """
        Iterate over mutations of the value for `key` in a dictionary.

        Args:
            input_dict (dict): The dictionary to mutate.
            key (str): The key whose value will be mutated.

        Yields:
            dict
        """
        print(f"== None value {key}")
        yield self._mutate_dict(input_dict, key, None)

        print(f"== Unicode value {key}")
        yield self._mutate_dict(input_dict, key, "\u9731")

        print(f"== int value {key}")
        yield self._mutate_dict(input_dict, key, 0)

    @staticmethod
    def _mutate_dict(input_dict, key, new_val):
        """
        Copy and update a dictionary.

        Args:
            input_dict (dict): The dictionary to copy and update.
            key (str): The key of the value to update.
            new_val: The new value to set for the key

        Returns:
            A copy of the dictionary with the value for `key` set to `new_val`.
        """
        mutated = copy.deepcopy(input_dict)
        mutated[key] = new_val
        return mutated

    @staticmethod
    def _mutate_list(input_list, index, new_val):
        """
        Copy and update a list.

        Args:
            input_list (list): The list to copy and update.
            index (int): The index of the value to update.
            new_val: The new value to set at the index.

        Returns:
            A copy of the list with the value at `index` set to `new_val`.
        """
        mutated = copy.deepcopy(input_list)
        mutated[index] = new_val
        return mutated


@ddt.ddt
class TestParsePromptsFromXml(TestCase):
    """
    Test deserialization of prompts data from XML.
    """
    @ddt.file_data("data/parse_prompts_xml.json")
    def test_parse_prompts_from_xml(self, data):
        xml = etree.fromstring("".join(data['xml']))
        prompts = _parse_prompts_xml(xml)

        self.assertEqual(prompts, data['prompts'])


@ddt.ddt
class TestParseRubricFromXml(TestCase):
    """
    Test deserialization of Rubric from XML.
    """

    @ddt.file_data("data/parse_rubric_xml.json")
    def test_parse_rubric_from_xml(self, data):
        xml = etree.fromstring("".join(data['xml']))
        rubric = parse_rubric_xml(xml)

        self.assertEqual(rubric['feedbackprompt'], data['feedbackprompt'])
        self.assertEqual(rubric['criteria'], data['criteria'])


@ddt.ddt
class TestParseExamplesFromXml(TestCase):
    """
    Test deserialization of examples from XML.
    """

    @ddt.file_data("data/parse_examples_xml.json")
    def test_parse_examples_from_xml(self, data):
        xml = etree.fromstring("".join(data['xml']))
        examples = parse_examples_xml(xml)
        self.assertEqual(examples, data['examples'])


@ddt.ddt
class TestParseAssessmentsFromXml(TestCase):
    """
    Test deserialization of assessments from XML.
    """

    @ddt.file_data("data/parse_assessments_xml.json")
    def test_parse_assessments_from_xml(self, data):
        xml = etree.fromstring("".join(data['xml']))
        assessments = parse_assessments_xml(xml)
        self.assertEqual(assessments, data['assessments'])


@ddt.ddt
class TestParseFromXml(TestCase):
    """
    Test deserialization of OpenAssessment XBlock content from XML.
    """
    maxDiff = None

    @ddt.file_data('data/update_from_xml.json')
    def test_parse_from_xml(self, data):

        # Update the block based on the fixture XML definition
        config = parse_from_xml_str("".join(data['xml']))

        # Check that the contents of the modified XBlock are correct
        expected_fields = [
            'title',
            'prompts',
            'start',
            'due',
            'submission_start',
            'submission_due',
            'criteria',
            'assessments',
            'file_upload_type',
            'white_listed_file_types',
            'allow_multiple_files',
            'allow_latex',
            'leaderboard_show'
        ]
        for field_name in expected_fields:
            if field_name in data:
                actual = config[field_name]
                expected = data[field_name]

                if field_name in ['start', 'due']:
                    expected = _parse_date(expected)

                self.assertEqual(
                    actual, expected,
                    msg="Wrong value for '{key}': was {actual} but expected {expected}".format(
                        key=field_name,
                        actual=repr(actual),
                        expected=repr(expected)
                    )
                )

    @ddt.file_data('data/update_from_xml_error.json')
    def test_parse_from_xml_error(self, data):
        with self.assertRaises(UpdateFromXmlError):
            parse_from_xml_str("".join(data['xml']))
