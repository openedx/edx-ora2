"""
Define the schema (expected format) of data.
Used to validate serialized data.
"""
from .record import Record


class ValidationError(Exception):
    """Validation errors occurred while loading the data."""

    def __init__(self, errors):
        """Initialize the error.

        Args:
            errors (list of unicode): List of validation error messages.

        Returns:
            ValidationError

        """
        self.errors = errors
        msg = u"Validation errors occurred: {errors}".format(
            errors="; ".join(self.errors)
        )
        super(ValidationError, self).__init__(msg)


class SchemaConfigError(Exception):
    """The schema is misconfigured."""
    pass


class Schema(object):
    """
    Represent the schema (expected format) of data.

    To define a new data type, create a subclass of `Schema`
    and add `SchemaField` class attributes.

    Example usage:

    >>> class PersonSchema(Schema):
    >>>     first_name = SchemaField(unicode)
    >>>     last_name = SchemaField(unicode)
    >>>     favorite_foods = ListField(
    >>>         RecordField({
    >>>             'name': SchemaField(unicode),
    >>>             'group': SchemaField(unicode, choices=["fruit", "vegetable", "protein", "grain"])
    >>>         })
    >>>     )
    >>>
    >>> person_data = PersonSchema().load_from_dict({
    >>>     'first_name': 'Bob',
    >>>     'last_name': 'Smith',
    >>>     'favorite_foods': [
    >>>         {
    >>>             'name': 'apple',
    >>>             'group': 'fruit'
    >>>         },
    >>>         {
    >>>             'name': 'bread',
    >>>             'group': 'grain'
    >>>         },
    >>>     ]
    >>> })
    >>>
    >>> person_data.first_name
    >>> "Bob"
    >>> person_data.favorite_foods[0].group
    >>> "fruit"

    """
    def record_from_dict(self, dict_data):
        """Load the data from a dictionary.

        Args:
            dict_data (dict): A dictionary representation of the data.

        Raises:
            ValidationError

        Returns:
            Record

        """
        # Create a dictionary schema field using the `SchemaField` attributes
        # of this class.
        schema_field_dict = {
            attr_name: attr_value
            for attr_name, attr_value in self.__class__.__dict__.iteritems()
            if isinstance(attr_value, SchemaField)
        }
        dict_field = RecordField(schema_field_dict)

        # Validate the dictionary
        errors = dict_field.validate(dict_data)
        if errors:
            raise ValidationError(errors)

        # Load the dictionary into a data object
        return dict_field.load_value(dict_data)


class TypeConverter(object):
    """ Convert a value of one type to another. """
    def __init__(self, from_type, to_type, convert_func):
        """
        Configure the converter.

        Args:
            from_type (type): The type to convert from.
            to_type (type): The type to convert to.
            convert_func (callable): Function that converts its argument to
                the specified output type.

        Returns:
            TypeConverter
        """
        self.from_type = from_type
        self.to_type = to_type
        self.convert_func = convert_func

    def matches(self, data_type, value):
        """Check whether the converter can be applied.

        Args:
            data_type (type): The type we're converting to.
            value: The value to be converted.

        Returns:
            bool
        """
        return isinstance(value, self.from_type) and data_type is self.to_type

    def convert(self, value):
        """Perform the type conversion."""
        return self.convert_func(value)


class SchemaField(object):
    """
    Represent a field in a data schema.  The field describes the expected
    format of the data, including:
        * constraints on the data type or values
        * default values if the data does not specify this field

    """
    def __init__(
        self,
        data_type,
        default=None,
        required=False,
        choices=None,
        allow_none=False,
        require_exact_type=False,
        type_converters=None,
    ):
        """
        Configure a schema field.

        Args:
            data_type (type): A Python type allowed for this field.
                (This an be any callable that accepts one argument
                and returns a value of the expected type).

        Kwargs:
            default: A default value to use for the field if no value is provided.
            required (bool): If True, the data *must* include this field -- we can't use the default.
            allow_none (bool): Whether `None` values are allowed for the field.
            choices (list): If provided, the value for this field must be
                one of the values in this list.
            require_exact_type (bool): If True, do not allow implicit type conversion.
            type_converters (list of `TypeConverter`): TO DO

        Returns:
            SchemaField

        Raises:
            SchemaConfigError

        """
        if not required and default is None and not allow_none:
            msg = u"Default value cannot be `None` if `allow_none` is False"
            raise SchemaConfigError(msg)

        if default is not None and not isinstance(default, data_type):
            msg = u"Default value must be an instance of {data_type}".format(data_type=data_type.__name__)
            raise SchemaConfigError(msg)

        if choices is not None and default not in choices:
            msg = u"Default value \"{default}\" is not in the list of allowed values: {choices}".format(
                default=default, choices=choices
            )
            raise SchemaConfigError(msg)

        self.data_type = data_type
        self.allow_none = allow_none
        self.default = default
        self.choices = choices
        self.required = required
        self.require_exact_type = require_exact_type

        # Handle unicode as a special (but common) case
        # If we don't provide the encoding ourselves, `unicode()` will
        # raise a `UnicodeDecodeError` when it encounters non-ASCII
        # unicode, which is almost never what we want to happen.
        if type_converters is None:
            self.type_converters = [
                TypeConverter(str, unicode, lambda s: unicode(s, encoding='utf-8'))
            ]
        else:
            self.type_converters = type_converters

    def validate(self, value):
        """
        Validate the value using the field definition.

        Args:
            value: The value to validate.

        Returns:
            list of unicode error messages.

        """
        errors = []

        # Check the type
        if self.require_exact_type:
            if not isinstance(value, self.data_type):
                msg = u"Value must be a(n) \"{type_name}\"".format(
                    type_name=self.data_type.__name__
                )
                errors.append(msg)

        # Check None values
        if not self.allow_none and value is None:
            msg = u"Value cannot be None"
            errors.append(msg)

        # Try to perform the type conversion; if it fails, that's an error
        else:
            try:
                value = self.load_value(value)
            except (ValueError, TypeError):
                msg = u"Value must be convertible to \"{type_name}\"".format(
                    type_name=self.data_type.__name__
                )
                errors.append(msg)

        # Check allowed values
        if self.choices is not None and value not in self.choices:
            msg = u"Value is not one of the allowed values: {allowed}".format(
                allowed=", ".join(self.choices)
            )
            errors.append(msg)

        return errors

    def load_value(self, value):
        """
        Convert the value to the type for this field.

        Args:
            value: The value to load.

        Returns:
            the sanitized value

        Raises:
            TypeError
            ValueError

        """
        for converter in self.type_converters:
            if converter.matches(self.data_type, value):
                value = converter.convert(value)

        if isinstance(value, self.data_type):
            return value
        else:
            return self.data_type(value)


class ListField(SchemaField):
    """
    Define the expected contents of a list in the schema.
    """

    def __init__(self, item_field):
        """
        Configure the list schema definition.

        Args:
            item_field (SchemaField): The schema field definition for items in the list.

        Returns:
            ListField

        """
        super(ListField, self).__init__(list, default=[], require_exact_type=True)
        self.item_field = item_field

    def validate(self, value):
        """
        Validate a list value and all items in the list.

        Args:
            value: The value to validate, which should be a list.

        Returns:
            list of unicode errors

        """
        errors = super(ListField, self).validate(value)
        if not errors:
            for item in value:
                errors.extend(self.item_field.validate(item))
        return errors

    def load_value(self, value):
        """
        Load values from a list.

        Args:
            value: The value to load, which should be a list.

        Returns:
            list of `Record` objects or lists.

        """
        list_value = super(ListField, self).load_value(value)
        return [
            self.item_field.load_value(item)
            for item in list_value
        ]


class RecordField(SchemaField):
    """
    Define the expected contents of a record (dictionary).
    """
    def __init__(self, item_field_dict):
        """
        Configure the record definition.

        Args:
            item_field_dict (dict of SchemaField): A dictionary mapping
                record item names to `SchemaField` definitions.

        Returns:
            RecordField

        Raises:
            SchemaConfigError

        """
        super(RecordField, self).__init__(dict, default={}, require_exact_type=True)
        self.item_field_dict = item_field_dict

        # Check the key values to make sure we don't accidentally
        # overwrite an existing attribute in the `Record` class.
        record_attributes = dir(Record)
        for key in item_field_dict.keys():
            if key in record_attributes:
                msg = "Invalid key \"{key}\"".format(key=key)
                raise SchemaConfigError(msg)

    def validate(self, value):
        """
        Validate a dictionary value and all items in the dictionary.
        Keys that aren't in the record field definition will be ignored.

        Args:
            value: The value to validate, which should be a dict.

        Returns:
            list of unicode errors

        """
        errors = super(RecordField, self).validate(value)

        # If there are no errors at this point, we know that
        # the value is a dictionary.
        # Now validate the contents of the dictionary.
        if not errors:

            # Find missing required keys
            required_fields = set(
                key for key, field in self.item_field_dict.iteritems()
                if field.required
            )
            missing_keys = required_fields - set(value.keys())
            if len(missing_keys) > 0:
                msg = u"Missing required value(s): {missing}".format(
                    missing=", ".join(missing_keys)
                )
                errors.append(msg)

            # Validate each item
            for key, item in value.iteritems():
                item_field = self.item_field_dict.get(key)
                if item_field is not None:
                    errors.extend([
                        u"Validation error for \"{field}\": {error}".format(
                            field=key, error=error
                        )
                        for error in set(item_field.validate(item))
                    ])

        return errors

    def load_value(self, value):
        """
        Load values from a list.

        Args:
            value: The value to load, which should be a dict.

        Returns:
            `Record` object

        """
        dict_value = super(RecordField, self).load_value(value)
        record = Record()

        # Since we're iterating through the fields we expect,
        # this will implicitly filter out fields that are in the dictionary
        # but which are not part of the schema.
        for key, item_field in self.item_field_dict.iteritems():

            # Sanitize each item in the dictionary
            # Assume that we've already run validation,
            # so the value should have all the required keys.
            if key in dict_value:
                sanitized = item_field.load_value(dict_value[key])
            else:
                sanitized = item_field.default

            # Set the attribute on the data object
            record.set(key, sanitized)

        return record
