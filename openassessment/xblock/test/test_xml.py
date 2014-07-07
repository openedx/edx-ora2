# -*- coding: utf-8 -*-
"""
Tests for serializing to/from XML.
"""
import copy
import datetime as dt
import mock
import lxml.etree as etree
import pytz
import dateutil.parser
from django.test import TestCase
import ddt
from openassessment.xblock.openassessmentblock import OpenAssessmentBlock
from openassessment.xblock.xml import (
    serialize_content, parse_from_xml_str, parse_rubric_xml_str,
    parse_examples_xml_str, parse_assessments_xml_str,
    serialize_rubric_to_xml_str, serialize_examples_to_xml_str,
    serialize_assessments_to_xml_str, UpdateFromXmlError
)


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
    else:
        return dateutil.parser.parse(value).replace(tzinfo=pytz.utc)


@ddt.ddt
class TestSerializeContent(TestCase):
    """
    Test serialization of OpenAssessment XBlock content to XML.
    """
    BASIC_CRITERIA = [
        {
            "order_num": 0,
            "name": "Test criterion",
            "prompt": "Test criterion prompt",
            "feedback": "disabled",
            "options": [
                {
                    "order_num": 0,
                    "points": 0,
                    "name": "Maybe",
                    "explanation": "Maybe explanation"
                }
            ]
        }
    ]

    BASIC_ASSESSMENTS = [
        {
            "name": "student-training",
            "start": "2014-02-27T09:46:28.873926",
            "due": "2014-05-30T00:00:00.92926",
            "examples": [
                {
                    "answer": u"ẗëṡẗ äṅṡẅëṛ",
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
        }
    ]

    def setUp(self):
        """
        Mock the OA XBlock.
        """
        self.oa_block = mock.MagicMock(OpenAssessmentBlock)


    def _configure_xblock(self, data):
        self.oa_block.title = data['title']
        self.oa_block.prompt = data['prompt']
        self.oa_block.rubric_feedback_prompt = data['rubric_feedback_prompt']
        self.oa_block.start = _parse_date(data['start'])
        self.oa_block.due = _parse_date(data['due'])
        self.oa_block.submission_start = data['submission_start']
        self.oa_block.submission_due = data['submission_due']
        self.oa_block.rubric_criteria = data['criteria']
        self.oa_block.rubric_assessments = data['assessments']

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
            self.fail("Could not parse output XML:\n{}".format(xml))

        # Assume that the test data XML is valid; if not, this will raise an error
        # instead of a test failure.
        parsed_expected = etree.fromstring("".join(data['expected_xml']))

        # Pretty-print and reparse the expected XML
        pretty_expected = etree.tostring(parsed_expected, pretty_print=True, encoding='unicode')
        parsed_expected = etree.fromstring(pretty_expected)

        # Walk both trees, comparing elements and attributes
        actual_elements = [el for el in parsed_actual.getiterator()]
        expected_elements = [el for el in parsed_expected.getiterator()]
        self.assertEqual(
            len(actual_elements), len(expected_elements),
            msg=u"Incorrect XML output:\nActual: {}\nExpected: {}".format(xml, pretty_expected)
        )

        for actual, expected in zip(actual_elements, expected_elements):
            self.assertEqual(actual.tag, expected.tag)
            self.assertEqual(
                actual.text, expected.text,
                msg=u"Incorrect text for {tag}.  Expected '{expected}' but found '{actual}'".format(
                    tag=actual.tag, expected=expected.text, actual=actual.text
                )
            )
            self.assertItemsEqual(
                actual.items(), expected.items(),
                msg=u"Incorrect attributes for {tag}.  Expected {expected} but found {actual}".format(
                    tag=actual.tag, expected=expected.items(), actual=actual.items()
                )
            )

    @ddt.file_data('data/serialize.json')
    def test_serialize_rubric(self, data):
        self._configure_xblock(data)
        xml_str = serialize_rubric_to_xml_str(self.oa_block)
        self.assertIn("<rubric>", xml_str)
        if data['prompt']:
            self.assertNotIn(data['prompt'], xml_str)

    @ddt.file_data('data/serialize.json')
    def test_serialize_examples(self, data):
        self._configure_xblock(data)
        for assessment in data['assessments']:
            if 'student-training' == assessment['name'] and assessment['examples']:
                xml_str = serialize_examples_to_xml_str(assessment)
                self.assertIn(assessment['examples'][0]['answer'], xml_str)

    @ddt.file_data('data/serialize.json')
    def test_serialize_assessments(self, data):
        self._configure_xblock(data)
        xml_str = serialize_assessments_to_xml_str(self.oa_block)
        self.assertIn(data['assessments'][0]['name'], xml_str)

    def test_mutated_criteria_dict(self):
        self.oa_block.title = "Test title"
        self.oa_block.rubric_assessments = self.BASIC_ASSESSMENTS
        self.oa_block.start = None
        self.oa_block.due = None
        self.oa_block.submission_start = None
        self.oa_block.submission_due = None

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
                    msg = "Could not parse mutated criteria dict {criteria}\n{ex}".format(criteria=mutated_dict, ex=ex)
                    self.fail(msg)

    def test_mutated_assessments_dict(self):
        self.oa_block.title = "Test title"
        self.oa_block.rubric_criteria = self.BASIC_CRITERIA
        self.oa_block.start = None
        self.oa_block.due = None
        self.oa_block.submission_start = None
        self.oa_block.submission_due = None

        for assessment_dict in self.BASIC_ASSESSMENTS:
            for mutated_dict in self._dict_mutations(assessment_dict):
                self.oa_block.rubric_assessments = [mutated_dict]
                xml = serialize_content(self.oa_block)

                try:
                    etree.fromstring(xml)
                except Exception as ex:     # pylint:disable=W0703
                    msg = "Could not parse mutated assessment dict {assessment}\n{ex}".format(assessment=mutated_dict, ex=ex)
                    self.fail(msg)

    @ddt.data("title", "prompt", "start", "due", "submission_due", "submission_start")
    def test_mutated_field(self, field):
        self.oa_block.rubric_criteria = self.BASIC_CRITERIA
        self.oa_block.rubric_assessments = self.BASIC_ASSESSMENTS
        self.oa_block.start = None
        self.oa_block.due = None
        self.oa_block.submission_start = None
        self.oa_block.submission_due = None

        for mutated_value in [0, u"\u9282", None]:
            setattr(self.oa_block, field, mutated_value)
            xml = serialize_content(self.oa_block)

            try:
                etree.fromstring(xml)
            except Exception as ex:     # pylint:disable=W0703
                msg = "Could not parse mutated field {field} with value {value}\n{ex}".format(
                    field=field, value=mutated_value, ex=ex
                )
                self.fail(msg)

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
        for key, val in input_dict.iteritems():

            # Mutation #1: Remove the key
            print "== Removing key {}".format(key)
            yield {k:v for k, v in input_dict.iteritems() if k != key}

            if isinstance(val, dict):

                # Mutation #2: Empty dict
                print "== Emptying dict {}".format(key)
                yield self._mutate_dict(input_dict, key, dict())

                # Mutation #3-5: value mutations
                for mutated in self._value_mutations(input_dict, key):
                    yield mutated

                # Recursively mutate sub keys
                for sub_mutation in self._dict_mutations(val):
                    yield self._mutate_dict(input_dict, key, sub_mutation)

            elif isinstance(val, list):
                # Mutation #2: Empty list
                print "== Emptying list {}".format(key)
                yield self._mutate_dict(input_dict, key, list())

                # Mutation #3-5: value mutations
                for mutated in self._value_mutations(input_dict, key):
                    yield mutated

                # Recursively mutate sub-items
                for item in val:
                    if isinstance(item, dict):
                        for sub_mutation in self._dict_mutations(item):
                            yield self._mutate_dict(input_dict, key, sub_mutation)

            else:
                # Mutation #3-5: value mutations
                for mutated in self._value_mutations(input_dict, key):
                    yield mutated

    def _value_mutations(self, input_dict, key):
        """
        Iterate over mutations of the value for `key` in a dictionary.

        Args:
            input_dict (dict): The dictionary to mutate.
            key (str): The key whose value will be mutated.

        Yields:
            dict
        """
        print "== None value {}".format(key)
        yield self._mutate_dict(input_dict, key, None)

        print "== Unicode value {}".format(key)
        yield self._mutate_dict(input_dict, key, u"\u9731")

        print "== int value {}".format(key)
        yield self._mutate_dict(input_dict, key, 0)

    def _mutate_dict(self, input_dict, key, new_val):
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

@ddt.ddt
class TestParseRubricFromXml(TestCase):

    @ddt.file_data("data/parse_rubric_xml.json")
    def test_parse_rubric_from_xml(self, data):
        rubric = parse_rubric_xml_str("".join(data['xml']))

        self.assertEqual(rubric['prompt'], data['prompt'])
        self.assertEqual(rubric['feedbackprompt'], data['feedbackprompt'])
        self.assertEqual(rubric['criteria'], data['criteria'])


@ddt.ddt
class TestParseExamplesFromXml(TestCase):

    @ddt.file_data("data/parse_examples_xml.json")
    def test_parse_examples_from_xml(self, data):
        examples = parse_examples_xml_str("".join(data['xml']))

        self.assertEqual(examples, data['examples'])

@ddt.ddt
class TestParseAssessmentsFromXml(TestCase):

    @ddt.file_data("data/parse_assessments_xml.json")
    def test_parse_assessments_from_xml(self, data):
        assessments = parse_assessments_xml_str("".join(data['xml']))

        self.assertEqual(assessments, data['assessments'])


@ddt.ddt
class TestUpdateFromXml(TestCase):
    """
    Test deserialization of OpenAssessment XBlock content from XML.
    """
    maxDiff = None

    def setUp(self):
        """
        Mock the OA XBlock.
        """
        self.oa_block = mock.MagicMock(OpenAssessmentBlock)
        self.oa_block.title = ""
        self.oa_block.prompt = ""
        self.oa_block.rubric_criteria = dict()
        self.oa_block.rubric_assessments = list()

        self.oa_block.start = dt.datetime(2000, 1, 1).replace(tzinfo=pytz.utc)
        self.oa_block.due = dt.datetime(3000, 1, 1).replace(tzinfo=pytz.utc)
        self.oa_block.submission_start = "2000-01-01T00:00:00"
        self.oa_block.submission_due = "2000-01-01T00:00:00"

    @ddt.file_data('data/update_from_xml.json')
    def test_parse_from_xml(self, data):

        # Update the block based on the fixture XML definition
        config = parse_from_xml_str("".join(data['xml']))

        # Check that the contents of the modified XBlock are correct
        self.assertEqual(config['title'], data['title'])
        self.assertEqual(config['prompt'], data['prompt'])
        self.assertEqual(config['submission_start'], data['submission_start'])
        self.assertEqual(config['submission_due'], data['submission_due'])
        self.assertEqual(config['rubric_criteria'], data['criteria'])
        self.assertEqual(config['rubric_assessments'], data['assessments'])

    @ddt.file_data('data/update_from_xml_error.json')
    def test_parse_from_xml_error(self, data):
        with self.assertRaises(UpdateFromXmlError):
            parse_from_xml_str("".join(data['xml']))

