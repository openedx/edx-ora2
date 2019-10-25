# coding=utf-8
"""
Serializers common to all assessment types.
"""
from __future__ import absolute_import

from copy import deepcopy
import logging

from rest_framework import serializers
from rest_framework.fields import DateTimeField, IntegerField

from django.core.cache import cache

from openassessment.assessment.models import Assessment, AssessmentPart, Criterion, CriterionOption, Rubric

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class InvalidRubric(Exception):
    """This can be raised during the deserialization process."""
    def __init__(self, errors):
        Exception.__init__(self, repr(errors))
        self.errors = deepcopy(errors)


class CriterionOptionSerializer(serializers.ModelSerializer):
    """Serializer for :class:`CriterionOption`"""

    # Django Rest Framework v3 no longer requires `PositiveIntegerField`s
    # to be positive by default, so we need to explicitly set the `min_value`
    # on the serializer field.
    points = IntegerField(min_value=0)

    class Meta:
        model = CriterionOption
        fields = ('order_num', 'points', 'name', 'label', 'explanation')


class CriterionSerializer(serializers.ModelSerializer):
    """Serializer for :class:`Criterion`"""
    options = CriterionOptionSerializer(required=True, many=True)

    class Meta:
        model = Criterion
        fields = ('order_num', 'name', 'label', 'prompt', 'options', 'points_possible')


class RubricSerializer(serializers.ModelSerializer):
    """Serializer for :class:`Rubric`."""
    criteria = CriterionSerializer(required=True, many=True)

    class Meta:
        model = Rubric
        fields = ('id', 'content_hash', 'structure_hash', 'criteria', 'points_possible')

    def validate_criteria(self, value):
        """Make sure we have at least one Criterion in the Rubric."""
        if not value:
            raise serializers.ValidationError("Must have at least one criterion")
        return value

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

    def create(self, validated_data):
        """
        Create the rubric model, including its nested models.

        Args:
            validated_data (dict): Dictionary of validated data for the rubric,
                including nested Criterion and CriterionOption data.

        Returns:
            Rubric
        """
        criteria_data = validated_data.pop("criteria")
        rubric = Rubric.objects.create(**validated_data)

        # Create each nested criterion in the rubric, linking it to the rubric
        for criterion_dict in criteria_data:
            options_data = criterion_dict.pop("options")
            criterion = Criterion.objects.create(rubric=rubric, **criterion_dict)

            # Create each option in the criterion, linking it to the criterion
            CriterionOption.objects.bulk_create(
                CriterionOption(criterion=criterion, **option_dict)
                for option_dict in options_data
            )

        return rubric


class AssessmentPartSerializer(serializers.ModelSerializer):
    """Serializer for :class:`AssessmentPart`."""

    class Meta:
        model = AssessmentPart
        fields = ('option', 'criterion', 'feedback')


class AssessmentSerializer(serializers.ModelSerializer):
    """Simplified serializer for :class:`Assessment` that's lighter on the DB."""

    # Django Rest Framework v3 uses the Django setting `DATETIME_FORMAT`
    # when serializing datetimes.  This differs from v2, which always
    # returned a datetime.  To preserve the old behavior, we explicitly
    # set `format` to None.
    # http://www.django-rest-framework.org/api-guide/fields/#datetimefield
    scored_at = DateTimeField(format=None, required=False)

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
    for part in assessment.parts.order_by('criterion__order_num').all().select_related("criterion", "option"):
        criterion_dict = dict(rubric_dict["criteria"][part.criterion.order_num])
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
    assessment_dict["id"] = assessment.id

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
