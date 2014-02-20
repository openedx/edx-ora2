"""
Serializers are created to ensure models do not have to be accessed outside the
scope of the Tim APIs.
"""
from copy import deepcopy
from hashlib import sha1
import json

from rest_framework import serializers
from openassessment.peer.models import (
    Assessment, AssessmentPart, Criterion, CriterionOption, Rubric
)

class InvalidRubric(Exception):
    def __init__(self, errors):
        Exception.__init__(self, repr(errors))
        self.errors = deepcopy(errors)


class NestedModelSerializer(serializers.ModelSerializer):
    """Model Serializer that supports arbitrary nesting.

    The Django REST Framework does not currently support deserialization more
    than one level deep (so a parent and children). We want to be able to
    create a Rubric -> Criterion -> CriterionOption hierarchy.

    Much of the base logic already "just works" and serialization of arbritrary
    depth is supported. So we just override the save_object method to
    recursively link foreign key relations instead of doing it one level deep.

    We don't touch many-to-many relationships because we don't need to for our
    purposes.
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

        if getattr(obj, '_m2m_data', None):
            for accessor_name, object_list in obj._m2m_data.items():
                setattr(obj, accessor_name, object_list)
            del(obj._m2m_data)

        self.recursively_link_related(obj, **kwargs)


class CriterionOptionSerializer(NestedModelSerializer):
    class Meta:
        model = CriterionOption
        fields = ('order_num', 'points', 'name', 'explanation')


class CriterionSerializer(NestedModelSerializer):
    options = CriterionOptionSerializer(required=True, many=True)

    class Meta:
        model = Criterion
        fields = ('order_num', 'prompt', 'options')


    def validate_options(self, attrs, source):
        options = attrs[source]
        if not options:
            raise serializers.ValidationError(
                "Criterion must have at least one option."
            )
        return attrs


class RubricSerializer(NestedModelSerializer):
    criteria = CriterionSerializer(required=True, many=True)

    class Meta:
        model = Rubric
        fields = ('id', 'content_hash', 'criteria')


    def validate_criteria(self, attrs, source):
        criteria = attrs[source]
        if not criteria:
            raise serializers.ValidationError("Must have at least one criterion")
        return attrs

    #def validate(self, attrs):
        #total_possible = sum(
        #    max(option.get("points", 0) for option in criterion["options"])
        #    for criterion in attrs["criteria"]
        #)
    #    total_possible = sum(crit.points_possible() for crit in attrs['criteria'])

    #    if total_possible <= 0:
    #        raise serializers.ValidationError(
    #            "Rubric must have > 0 possible points."
    #        )


class AssessmentPartSerializer(serializers.ModelSerializer):
    option = CriterionOptionSerializer()

    class Meta:
        model = AssessmentPart
        fields = ('option',)


class AssessmentSerializer(serializers.ModelSerializer):
    parts = AssessmentPartSerializer(required=True, many=True)

    class Meta:
        model = Assessment
        fields = ('submission', 'rubric', 'scored_at', 'scorer_id', 'score_type')



def rubric_from_dict(rubric_dict):
    """Given a rubric_dict, return the rubric ID we're going to submit against.

    This will create the Rubric and its children if it does not exist already.
    """
    rubric_dict = deepcopy(rubric_dict)

    # Calculate the hash based on the rubric content...
    content_hash = Rubric.content_hash_for_rubric_dict(rubric_dict)

    try:
        rubric = Rubric.objects.get(content_hash=content_hash)
    except Rubric.DoesNotExist:
        rubric_dict["content_hash"] = content_hash
        rubric_serializer = RubricSerializer(data=rubric_dict)
        if not rubric_serializer.is_valid():
            raise InvalidRubric(rubric_serializer.errors)
        rubric = rubric_serializer.save()

    return rubric
