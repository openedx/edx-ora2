""" Serializer utilities for ORA MFE """
from rest_framework.fields import CharField, ListField


class CharListField(ListField):
    child = CharField()
