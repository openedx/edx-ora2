# coding=utf-8
"""
Tests for data schema.
"""
import copy
from unittest import TestCase
from .schema import (
    Schema, SchemaField, ListField, RecordField,
    ValidationError, SchemaConfigError
)


class ExampleSchema(Schema):
    """Example schema used for testing."""
    unicode_field = SchemaField(unicode, default=u"")
    not_none_field = SchemaField(unicode, default=u"", allow_none=False)
    optional_int_field = SchemaField(int, default=0)
    required_field = SchemaField(unicode, required=True)
    choice_field = SchemaField(unicode, choices=[u'green eggs', u'green ham'], default=u'green eggs')
    list_field = ListField(
        SchemaField(unicode, default=u"")
    )
    record_field = RecordField({
        'int_field': SchemaField(int, default=0),
        'unicode_field': SchemaField(unicode, default=u""),
        'optional_int_field': SchemaField(unicode, default=u"", required=False)
    })
    nested_record_in_list_field = ListField(
        RecordField({
            'key': SchemaField(int, default=0)
        })
    )
    nested_list_in_record_field = RecordField({
        'list_field': ListField(
            SchemaField(int, default=0)
        )
    })


class SchemaTest(TestCase):
    """
    Test schema validation.
    """
    DATA_DICT = {
        'unicode_field': u'ẗḧïṡ ïṡ öṅḷÿ ä ẗëṡẗ',
        'not_none_field': u'nøŧ nønɇ',
        'optional_int_field': 56,
        'required_field': u"required!",
        'choice_field': u'green eggs',
        'list_field': [
            u'item one',
            u'item two',
        ],
        'record_field': {
            'int_field': 4,
            'unicode_field': u'ẗḧïṡ ïṡ öṅḷÿ ä ẗëṡẗ',
        },
        'nested_record_in_list_field': [
            {'key': 9}, {'key': 10}
        ],
        'nested_list_in_record_field': {
            'list_field': [
                5, 6, 7, 8
            ]
        }
    }

    def setUp(self):
        self.schema = ExampleSchema()
        self.data_dict = copy.deepcopy(self.DATA_DICT)

    def test_fields(self):
        record = self.schema.record_from_dict(self.data_dict)

        # Check primitive types
        primitive_fields = [
            'unicode_field', 'not_none_field', 'optional_int_field',
            'required_field', 'choice_field', 'list_field'
        ]
        for key in primitive_fields:
            self.assertEqual(getattr(record, key), self.DATA_DICT[key])

        # Check complex types
        self.assertEqual(
            record.record_field.int_field,
            self.DATA_DICT['record_field']['int_field']
        )
        self.assertEqual(
            record.record_field.unicode_field,
            self.DATA_DICT['record_field']['unicode_field']
        )
        self.assertEqual(
            record.nested_record_in_list_field[0].key,
            self.DATA_DICT['nested_record_in_list_field'][0]['key']
        )
        self.assertEqual(
            record.nested_record_in_list_field[1].key,
            self.DATA_DICT['nested_record_in_list_field'][1]['key']
        )
        self.assertEqual(
            record.nested_list_in_record_field.list_field,
            self.DATA_DICT['nested_list_in_record_field']['list_field']
        )

        # Test conversion back to a dictionary
        self.assertItemsEqual(record.to_dict(), self.DATA_DICT)

    def test_default(self):
        # Remove a key that has a default value
        del self.data_dict['optional_int_field']

        # Expect that the default value is used
        record = self.schema.record_from_dict(self.data_dict)
        self.assertEqual(record.optional_int_field, 0)

    def test_choice(self):
        # Expect a validation error if we choose an option that isn't in the list of choices
        self.data_dict['choice_field'] = 'not an option'
        with self.assertRaises(ValidationError):
            self.schema.record_from_dict(self.data_dict)

    def test_missing_required(self):
        # Expect a validation error if we remove a key that's required
        del self.data_dict['required_field']
        with self.assertRaises(ValidationError):
            self.schema.record_from_dict(self.data_dict)

    def test_extra(self):
        # Add an extra field
        self.data_dict['extra'] = u'EXTRA!'

        # The schema should ignore the extra field
        record = self.schema.record_from_dict(self.data_dict)
        self.assertFalse(hasattr(record, 'extra'))

    def test_sanitize_data(self):
        # Implicit type conversion from unicode --> int
        self.data_dict['optional_int_field'] = '1'
        record = self.schema.record_from_dict(self.data_dict)
        self.assertEqual(record.optional_int_field, 1)

    def test_default_encoding(self):
        self.data_dict['unicode_field'] = u'\u2603'.encode('utf-8')
        record = self.schema.record_from_dict(self.data_dict)
        self.assertEqual(record.unicode_field, u'\u2603')

    def test_empty_list(self):
        self.data_dict['list_field'] = []
        record = self.schema.record_from_dict(self.data_dict)
        self.assertEqual(record.list_field, [])

    def test_not_a_list(self):
        self.data_dict['list_field'] = dict()
        with self.assertRaises(ValidationError):
            self.schema.record_from_dict(self.data_dict)

    def test_not_a_dict(self):
        self.data_dict['record_field'] = list()
        with self.assertRaises(ValidationError):
            self.schema.record_from_dict(self.data_dict)

    def test_type_conversion_error(self):
        self.data_dict['optional_int_field'] = "not an int!"
        with self.assertRaises(ValidationError):
            self.schema.record_from_dict(self.data_dict)

    def test_none_when_none_is_not_allowed(self):
        self.data_dict['not_none_field'] = None
        with self.assertRaises(ValidationError):
            self.schema.record_from_dict(self.data_dict)


class SchemaConfigErrorTest(TestCase):
    """
    Test misconfigured schema errors.
    """

    def test_default_is_none_if_none_not_allowed(self):
        with self.assertRaises(SchemaConfigError):
            SchemaField(int, default=None)

    def test_default_does_not_match_data_type(self):
        with self.assertRaises(SchemaConfigError):
            SchemaField(int, default="not an int")

    def test_default_not_in_choices(self):
        with self.assertRaises(SchemaConfigError):
            SchemaField(int, choices=[1, 2, 3], default=10)

    def test_invalid_record_field_name(self):
        with self.assertRaises(SchemaConfigError):
            RecordField({
                '__dict__': SchemaField(int, default=0)
            })
