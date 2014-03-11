# coding=utf-8
"""
Serializers are created to ensure models do not have to be accessed outside the
scope of the Tim APIs.
"""
from copy import deepcopy

from django.utils.translation import ugettext as _
from rest_framework import serializers
from openassessment.assessment.models import (
    Assessment, AssessmentPart, Criterion, CriterionOption, Rubric
)


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
        fields = ('order_num', 'points', 'name', 'explanation')


class CriterionSerializer(NestedModelSerializer):
    """Serializer for :class:`Criterion`"""
    options = CriterionOptionSerializer(required=True, many=True)

    class Meta:
        model = Criterion
        fields = ('order_num', 'name', 'prompt', 'options')

    def validate_options(self, attrs, source):
        """Make sure we have at least one CriterionOption in a Criterion."""
        options = attrs[source]
        if not options:
            raise serializers.ValidationError(
                "Criterion must have at least one option."
            )
        return attrs


class RubricSerializer(NestedModelSerializer):
    """Serializer for :class:`Rubric`."""
    criteria = CriterionSerializer(required=True, many=True)
    points_possible = serializers.Field(source='points_possible')

    class Meta:
        model = Rubric
        fields = ('id', 'content_hash', 'criteria', 'points_possible')

    def validate_criteria(self, attrs, source):
        """Make sure we have at least one Criterion in the Rubric."""
        criteria = attrs[source]
        if not criteria:
            raise serializers.ValidationError("Must have at least one criterion")
        return attrs


class AssessmentPartSerializer(serializers.ModelSerializer):
    """Serializer for :class:`AssessmentPart`."""

    class Meta:
        model = AssessmentPart
        fields = ('option',)  # TODO: Direct link to Criterion?


class AssessmentSerializer(serializers.ModelSerializer):
    """Serializer for :class:`Assessment`."""
    submission_uuid = serializers.Field(source='submission_uuid')

    parts = AssessmentPartSerializer(required=True, many=True)
    points_earned = serializers.Field(source='points_earned')
    points_possible = serializers.Field(source='points_possible')

    class Meta:
        model = Assessment
        fields = (
            'submission',  # will go away shortly
            'rubric',
            'scored_at',
            'scorer_id',
            'score_type',
            'feedback',

            # Foreign Key
            'parts',

            # Computed, not part of the model
            'submission_uuid',
            'points_earned',
            'points_possible',
        )


def get_assessment_review(submission):
    """Get all information pertaining to an assessment for review.

    Given an assessment serializer, return a serializable formatted model of
    the assessment, all assessment parts, all criterion options, and the
    associated rubric.

    Args:
        submission (Submission): The Submission Model object to get
            assessment reviews for.

    Returns:
        (list): A list of assessment reviews, combining assessments with
            rubrics and assessment parts, to allow a cohesive object for
            rendering the complete peer grading workflow.

    Examples:
        >>> get_assessment_review(submission, score_type)
        [{
            'submission': 1,
            'rubric': {
                'id': 1,
                'content_hash': u'45cc932c4da12a1c2b929018cd6f0785c1f8bc07',
                'criteria': [{
                    'order_num': 0,
                    'name': u'Spelling',
                    'prompt': u'Did the student have spelling errors?',
                    'options': [{
                        'order_num': 0,
                        'points': 2,
                        'name': u'No spelling errors',
                        'explanation': u'No spelling errors were found in this submission.',
                    }]
                }]
            },
            'scored_at': datetime.datetime(2014, 2, 25, 19, 50, 7, 290464, tzinfo=<UTC>),
            'scorer_id': u'Bob',
            'score_type': u'PE',
            'parts': [{
                'option': {
                    'order_num': 0,
                    'points': 2,
                    'name': u'No spelling errors',
                    'explanation': u'No spelling errors were found in this submission.'}
                }],
            'submission_uuid': u'0a600160-be7f-429d-a853-1283d49205e7',
            'points_earned': 9,
            'points_possible': 20,
        }]
    """
    return [
        full_assessment_dict(assessment)
        for assessment in Assessment.objects.filter(submission=submission)
    ]


def full_assessment_dict(assessment):
    """
    Return a dict representation of the Assessment model,
    including nested assessment parts.

    Args:
        assessment (Assessment): The Assessment model to serialize

    Returns:
        dict with keys 'rubric' (serialized Rubric model) and 'parts' (serialized assessment parts)
    """
    assessment_dict = AssessmentSerializer(assessment).data
    rubric_dict = RubricSerializer(assessment.rubric).data
    assessment_dict["rubric"] = rubric_dict
    parts = []
    for part in assessment.parts.all():
        part_dict = AssessmentPartSerializer(part).data
        options_dict = CriterionOptionSerializer(part.option).data
        criterion_dict = CriterionSerializer(part.option.criterion).data
        options_dict["criterion"] = criterion_dict
        part_dict["option"] = options_dict
        parts.append(part_dict)
    assessment_dict["parts"] = parts
    return assessment_dict


def rubric_from_dict(rubric_dict):
    """Given a dict of rubric information, return the corresponding Rubric

    This will create the Rubric and its children if it does not exist already.

    Sample data (one criterion, two options)::

        {
          "prompt": "Create a plan to deliver edx-tim!",
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
