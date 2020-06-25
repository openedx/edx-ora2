"""
Django models for training (both student and AI).
"""


from hashlib import sha1
import json

from django.core.cache import cache
from django.db import models

from .base import CriterionOption, Rubric


class TrainingExample(models.Model):
    """
    An example assessment used to train students (before peer assessment) or AI.
    """
    # The answer (JSON-serialized)
    raw_answer = models.TextField(blank=True)

    rubric = models.ForeignKey(Rubric, on_delete=models.CASCADE)

    # Use a m2m to avoid changing the criterion option
    options_selected = models.ManyToManyField(CriterionOption)

    # SHA1 hash
    content_hash = models.CharField(max_length=40, unique=True, db_index=True)

    class Meta:
        app_label = "assessment"

    @classmethod
    def create_example(cls, answer, options_selected, rubric):
        """
        Create a new training example.

        Args:
            answer (JSON-serializable): The answer associated with the training example.
            options_selected (dict): The options selected from the rubric (mapping of criterion names to option names)
            rubric (Rubric): The rubric associated with the training example.

        Returns:
            TrainingExample

        Raises:
            InvalidRubricSelection

        """
        content_hash = cls.calculate_hash(answer, options_selected, rubric)
        example = TrainingExample.objects.create(
            content_hash=content_hash,
            raw_answer=json.dumps(answer),
            rubric=rubric
        )

        # This will raise `InvalidRubricSelection` if the selected options
        # do not match the rubric.
        for criterion_name, option_name in options_selected.items():
            option = rubric.index.find_option(criterion_name, option_name)
            example.options_selected.add(option)
        return example

    @property
    def answer(self):
        """
        Return the JSON-decoded answer.

        Returns:
            JSON-serializable

        """
        return json.loads(self.raw_answer)

    @property
    def options_selected_dict(self):
        """
        Return a dictionary of the rubric options selected.

        Returns:
            dict: maps criterion names to selected option names

        """
        # Since training examples are immutable, we can safely cache this
        cache_key = self.cache_key_serialized(attribute="options_selected_dict")
        options_selected = cache.get(cache_key)
        if options_selected is None:
            options_selected = {
                option.criterion.name: option.name
                for option in self.options_selected.all()
            }
            cache.set(cache_key, options_selected)
        return options_selected

    def cache_key_serialized(self, attribute=None):
        """
        Create a cache key based on the content hash
        for serialized versions of this model.

        Keyword Arguments:
            attribute: The name of the attribute being serialized.
                If not specified, assume that we are serializing the entire model.

        Returns:
            str: The cache key

        """
        if attribute is None:
            key_template = u"TrainingExample.json.{content_hash}"
        else:
            key_template = u"TrainingExample.{attribute}.json.{content_hash}"

        cache_key = key_template.format(
            content_hash=self.content_hash,
            attribute=attribute
        )
        return cache_key

    @staticmethod
    def calculate_hash(answer, options_selected, rubric):
        """
        Calculate a hash for the contents of training example.

        Args:
            answer (JSON-serializable): The answer associated with the training example.
            options_selected (dict): The options selected from the rubric (mapping of criterion names to option names)
            rubric (Rubric): The rubric associated with the training example.

        Returns:
            str

        """
        contents = json.dumps({
            'answer': answer,
            'options_selected': options_selected,
            'rubric': rubric.id
        })
        return sha1(contents.encode('utf-8')).hexdigest()

    @classmethod
    def cache_key(cls, answer, options_selected, rubric):
        """
        Calculate a cache key based on the content hash.

        Args:
            answer (JSON-serializable): The answer associated with the training example.
            options_selected (dict): The options selected from the rubric (mapping of criterion names to option names)
            rubric (Rubric): The rubric associated with the training example.

        Returns:
            tuple of `(cache_key, content_hash)`, both bytestrings

        """
        content_hash = cls.calculate_hash(answer, options_selected, rubric)
        cache_key = u"TrainingExample.model.{content_hash}".format(
            content_hash=content_hash
        )
        return cache_key, content_hash
