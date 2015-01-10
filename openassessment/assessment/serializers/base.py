# coding=utf-8
"""
Serializers common to all assessment types.
"""
from copy import deepcopy
import logging

from django.core.cache import cache
from rest_framework import serializers
from openassessment.assessment.models import (
    Assessment, AssessmentPart, Criterion, CriterionOption, Rubric,
)


logger = logging.getLogger(__name__)


class InvalidRubric(Exception):
    """This can be raised during the deserialization process."""
    def __init__(self, errors):
        Exception.__init__(self, repr(errors))
        self.errors = deepcopy(errors)


class NestedModelSerializer(serializers.ModelSerializer):
    """Model Serializer that supports deserialization with arbitrary nesting.

    The Django REST Framework does not currently support deserialization more
    than one level deep (so a parent and children). We want to be able to
    create a :class:`Rubric` → :class:`Criterion` → :class:`CriterionOption`
    hierarchy.

    Much of the base logic already "just works" and serialization of arbritrary
    depth is supported. So we just override the save_object method to
    recursively link foreign key relations instead of doing it one level deep.

    We don't touch many-to-many relationships because we don't need to for our
    purposes, so those still only work one level deep.
    """
    def recursively_link_related(self, obj, **kwargs):
        if getattr(obj, '_related_data', None):
            for accessor_name, related in obj._related_data.items():
                setattr(obj, accessor_name, related)
                for related_obj in related:
                    self.recursively_link_related(related_obj, **kwargs)
            del(obj._related_data)

    def save_object(self, obj, **kwargs):
        obj.save(**kwargs)

        # The code for many-to-many relationships is just copy-pasted from the
        # Django REST Framework ModelSerializer
        if getattr(obj, '_m2m_data', None):
            for accessor_name, object_list in obj._m2m_data.items():
                setattr(obj, accessor_name, object_list)
            del(obj._m2m_data)

        # This is our only real change from ModelSerializer
        self.recursively_link_related(obj, **kwargs)


class CriterionOptionSerializer(NestedModelSerializer):
    """Serializer for :class:`CriterionOption`"""
    class Meta:
        model = CriterionOption
        fields = ('order_num', 'points', 'name', 'label', 'explanation')


class CriterionSerializer(NestedModelSerializer):
    """Serializer for :class:`Criterion`"""
    options = CriterionOptionSerializer(required=True, many=True)
    points_possible = serializers.Field(source='points_possible')

    class Meta:
        model = Criterion
        fields = ('order_num', 'name', 'label', 'prompt', 'options', 'points_possible')


class RubricSerializer(NestedModelSerializer):
    """Serializer for :class:`Rubric`."""
    criteria = CriterionSerializer(required=True, many=True)
    points_possible = serializers.Field(source='points_possible')

    class Meta:
        model = Rubric
        fields = ('id', 'content_hash', 'structure_hash', 'criteria', 'points_possible')

    def validate_criteria(self, attrs, source):
        """Make sure we have at least one Criterion in the Rubric."""
        criteria = attrs[source]
        if not criteria:
            raise serializers.ValidationError("Must have at least one criterion")
        return attrs

    @classmethod
    def serialized_from_cache(cls, rubric, local_cache=None):
        """For a given `Rubric` model object, return a serialized version.

        This method will attempt to use the cache if possible, first looking at
        the `local_cache` dict you can pass in, and then looking at whatever
        Django cache is configured.

        Args:
            rubric (Rubric): The Rubric model to get the serialized form of.
            local_cach (dict): Mapping of `rubric.content_hash` to serialized
                rubric dictionary. We include this so that we can call this
                method in a loop.

        Returns:
            dict: `Rubric` fields as a dictionary, with `criteria` and `options`
                relations followed.
        """
        # Optional local cache you can send in (for when you're calling this
        # in a loop).
        local_cache = local_cache or {}

        # Check our in-memory cache...
        if rubric.content_hash in local_cache:
            return local_cache[rubric.content_hash]

        # Check the external cache (e.g. memcached)
        rubric_dict_cache_key = (
            "RubricSerializer.serialized_from_cache.{}"
            .format(rubric.content_hash)
        )
        rubric_dict = cache.get(rubric_dict_cache_key)
        if rubric_dict:
            local_cache[rubric.content_hash] = rubric_dict
            return rubric_dict

        # Grab it from the database
        rubric_dict = RubricSerializer(rubric).data
        cache.set(rubric_dict_cache_key, rubric_dict)
        local_cache[rubric.content_hash] = rubric_dict

        return rubric_dict


class AssessmentPartSerializer(serializers.ModelSerializer):
    """Serializer for :class:`AssessmentPart`."""

    class Meta:
        model = AssessmentPart
        fields = ('option', 'criterion', 'feedback')


class AssessmentSerializer(serializers.ModelSerializer):
    """Simplified serializer for :class:`Assessment` that's lighter on the DB."""

    class Meta:
        model = Assessment
        fields = (
            'submission_uuid',
            'rubric',
            'scored_at',
            'scorer_id',
            'score_type',
            'feedback',
        )


def serialize_assessments(assessments_qset):
    assessments = list(assessments_qset.select_related("rubric"))
    rubric_cache = {}

    return [
        full_assessment_dict(
            assessment,
            RubricSerializer.serialized_from_cache(
                assessment.rubric, rubric_cache
            )
        )
        for assessment in assessments
    ]


def full_assessment_dict(assessment, rubric_dict=None):
    """
    Return a dict representation of the Assessment model, including nested
    assessment parts. We do some of the serialization ourselves here instead
    of relying on the Django REST Framework serializers. This is for performance
    reasons -- we have a cached rubric easily available, and we don't want to
    follow all the DB relations from assessment -> assessment part -> option ->
    criterion.

    Args:
        assessment (Assessment): The Assessment model to serialize

    Returns:
        dict with keys 'rubric' (serialized Rubric model) and 'parts' (serialized assessment parts)
    """
    assessment_cache_key = "assessment.full_assessment_dict.{}.{}.{}".format(
        assessment.id, assessment.submission_uuid, assessment.scored_at.isoformat()
    )
    assessment_dict = cache.get(assessment_cache_key)
    if assessment_dict:
        return assessment_dict

    assessment_dict = AssessmentSerializer(assessment).data
    if not rubric_dict:
        rubric_dict = RubricSerializer.serialized_from_cache(assessment.rubric)

    assessment_dict["rubric"] = rubric_dict

    # This part looks a little goofy, but it's in the name of saving dozens of
    # SQL lookups. The rubric_dict has the entire serialized output of the
    # `Rubric`, its child `Criterion` and grandchild `CriterionOption`. This
    # includes calculated things like `points_possible` which aren't actually in
    # the DB model. Instead of invoking the serializers for `Criterion` and
    # `CriterionOption` again, we simply index into the places we expect them to
    # be from the big, saved `Rubric` serialization.
    parts = []
    for part in assessment.parts.all().select_related("criterion", "option"):
        criterion_dict = rubric_dict["criteria"][part.criterion.order_num]
        options_dict = None
        if part.option is not None:
            options_dict = criterion_dict["options"][part.option.order_num]
            options_dict["criterion"] = criterion_dict
        parts.append({
            "option": options_dict,
            "criterion": criterion_dict,
            "feedback": part.feedback
        })

    # Now manually built up the dynamically calculated values on the
    # `Assessment` so we can again avoid DB calls.
    assessment_dict["parts"] = parts
    assessment_dict["points_earned"] = sum(
        part_dict["option"]["points"]
        if part_dict["option"] is not None else 0
        for part_dict in parts
    )
    assessment_dict["points_possible"] = rubric_dict["points_possible"]

    cache.set(assessment_cache_key, assessment_dict)

    return assessment_dict


def rubric_from_dict(rubric_dict):
    """Given a dict of rubric information, return the corresponding Rubric

    This will create the Rubric and its children if it does not exist already.

    Sample data (one criterion, two options)::

        {
          "prompts": [{"description": "Create a plan to deliver ora2!"}],
          "criteria": [
            {
              "order_num": 0,
              "name": "realistic",
              "prompt": "Is the deadline realistic?",
              "options": [
                {
                  "order_num": 0,
                  "points": 0,
                  "name": "No",
                  "explanation": "We need more time!"
                },
                {
                  "order_num": 1,
                  "points": 2,
                  "name": "Yes",
                  "explanation": "We got this."
                },
              ]
            }
          ]
        }

    """
    rubric_dict = deepcopy(rubric_dict)

    # Calculate the hash based on the rubric content...
    content_hash = Rubric.content_hash_from_dict(rubric_dict)

    try:
        rubric = Rubric.objects.get(content_hash=content_hash)
    except Rubric.DoesNotExist:
        rubric_dict["content_hash"] = content_hash
        rubric_dict["structure_hash"] = Rubric.structure_hash_from_dict(rubric_dict)
        for crit_idx, criterion in enumerate(rubric_dict.get("criteria", {})):
            if "order_num" not in criterion:
                criterion["order_num"] = crit_idx
            for opt_idx, option in enumerate(criterion.get("options", {})):
                if "order_num" not in option:
                    option["order_num"] = opt_idx

        rubric_serializer = RubricSerializer(data=rubric_dict)
        if not rubric_serializer.is_valid():
            raise InvalidRubric(rubric_serializer.errors)
        rubric = rubric_serializer.save()

    return rubric
