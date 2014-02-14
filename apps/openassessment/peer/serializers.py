"""
Serializers are created to ensure models do not have to be accessed outside the
scope of the Tim APIs.
"""
from copy import deepcopy
from hashlib import sha1
import json

from rest_framework import serializers
from openassessment.peer.models import (
    Criterion, CriterionOption, PeerEvaluation, Rubric
)


class PeerAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeerEvaluation
        fields = (
            'submission',
            'points_earned',
            'points_possible',
            'scored_at',
            'scorer_id',
            'score_type',
            'feedback',
        )


class CriterionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CriterionOption
        fields = ('order_num', 'points', 'name', 'explanation')


class CriterionSerializer(serializers.ModelSerializer):
    options = CriterionOptionSerializer(many=True)

    class Meta:
        model = Criterion
        fields = ('order_num', 'prompt', 'options')


class RubricSerializer(serializers.ModelSerializer):
    criteria = CriterionSerializer(many=True)

    class Meta:
        model = Rubric
        fields = ('id', 'content_hash', 'prompt', 'criteria')


def content_hash_for_rubric_dict(rubric_dict):
    """
    It's passing in the results from a RubricSerializer, so we just have to get
    rid of the content_hash.
    """
    rubric_dict = deepcopy(rubric_dict)
    # Neither "id" nor "content_hash" would count towards calculating the
    # content_hash.
    rubric_dict.pop("id", None)
    rubric_dict.pop("content_hash", None)

    canonical_form = json.dumps(rubric_dict, sort_keys=True)
    return sha1(canonical_form).hexdigest()

def rubric_id_for(rubric_dict):
    """Given a rubric_dict, return the rubric ID we're going to submit against.

    This will create the Rubric and its children if it does not exist already.
    """
    rubric_dict = deepcopy(rubric_dict)

    # Calculate the hash based on the rubric content...
    content_hash = content_hash_for_rubric_dict(rubric_dict)

    try:
        rubric = Rubric.objects.get(content_hash=content_hash)
    except Rubric.DoesNotExist:
        rubric_dict["content_hash"] = content_hash
        rubric_serializer = RubricSerializer(data=rubric_dict)
        if not rubric_serializer.is_valid():
            raise ValueError("Some better Exception here")

        rubric = rubric_serializer.save()

    return rubric.id
