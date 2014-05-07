"""
Django models for training (both student and AI).
"""
import json
from hashlib import sha1
from django.db import models
from .base import Rubric, CriterionOption


class TrainingExample(models.Model):
    """
    An example assessment used to train students (before peer assessment) or AI.
    """
    # The answer (JSON-serialized)
    raw_answer = models.TextField(blank=True)

    rubric = models.ForeignKey(Rubric)

    # Use a m2m to avoid changing the criterion option
    options_selected = models.ManyToManyField(CriterionOption)

    # SHA1 hash
    content_hash = models.CharField(max_length=40, unique=True, db_index=True)

    class Meta:
        app_label = "assessment"

    @classmethod
    def create_example(cls, answer, options_ids, rubric):
        """
        Create a new training example.

        Args:
            answer (JSON-serializable): The answer associated with the training example.
            option_ids (iterable of int): Selected option IDs for the training example.
            rubric (Rubric): The rubric associated with the training example.

        Returns:
            TrainingExample

        """
        content_hash = cls.calculate_hash(answer, options_ids, rubric)
        example = TrainingExample.objects.create(
            content_hash=content_hash,
            raw_answer=json.dumps(answer),
            rubric=rubric
        )

        for option in CriterionOption.objects.filter(pk__in=list(options_ids)):
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
        return {
            option.criterion.name: option.name
            for option in self.options_selected.all()  # pylint:disable=E1101
        }

    @staticmethod
    def calculate_hash(answer, option_ids, rubric):
        """
        Calculate a hash for the contents of training example.

        Args:
            answer (JSON-serializable): The answer associated with the training example.
            option_ids (iterable of int): Selected option IDs for the training example.
            rubric (Rubric): The rubric associated with the training example.

        Returns:
            str

        """
        contents = json.dumps({
            'answer': answer,
            'option_ids': list(option_ids),
            'rubric': rubric.id
        })
        return sha1(contents).hexdigest()

    class Meta:
        app_label = "assessment"
