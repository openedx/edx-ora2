"""
Some custom serializer types and utils we use across our MFE
"""

from rest_framework.fields import BooleanField, CharField, ListField

# Map workflow step name to serialized values
STEP_NAME_MAPPINGS = {
    "submission": "submission",
    "peer": "peer",
    "training": "studentTraining",
    "self": "self",
    "teams": "teams",
    "ai": "ai",
    "waiting": "waiting",
    "staff": "staff",
    "done": "done",
    "cancelled": "submission",
}


class CharListField(ListField):
    """
    Shorthand for serializing a list of strings (CharFields)
    """

    child = CharField()


class IsRequiredField(BooleanField):
    """
    Utility for checking if a field is "required" to reduce repeated code.
    """

    def to_representation(self, value):
        return value == "required"


class NullField(CharField):
    """
    A field which returns a Null/None value
    """

    def to_representation(self, value):
        return None
