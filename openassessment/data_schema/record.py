"""
Serialize and deserialize data.
"""

class Record(object):
    """
    Represent data that can be serialized in different formats.
    """

    def __init__(self):
        """
        Create a new (empty) data object.

        Returns:
            Data

        """
        self._fields = {}

    def to_dict(self):
        """
        Serialize the data to a dictionary.

        Returns:
            dict: The serialized data

        """
        # We use dictionaries internally, so we can just return that
        return self._fields

    def set(self, key, value):
        self._fields[key] = value

    def __getattr__(self, name):
        if name in self._fields:
            return self._fields[name]
        else:
            raise AttributeError(name)
