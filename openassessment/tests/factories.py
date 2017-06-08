"""
Create factories for assessments and all of their related models.
"""
import factory
from factory.django import DjangoModelFactory

from openassessment.assessment.models import (
    Assessment, AssessmentPart, Rubric, Criterion, CriterionOption, AssessmentFeedbackOption, AssessmentFeedback
)


class RubricFactory(DjangoModelFactory):
    """ Create mock Rubric models. """
    class Meta:
        model = Rubric

    content_hash = factory.Faker('sha1')
    structure_hash = factory.Faker('sha1')


class CriterionFactory(DjangoModelFactory):
    """
    Create mock Criterion models.

    Currently assumes there is only one Rubric that these are attached to.
    """
    class Meta:
        model = Criterion

    rubric = factory.SubFactory(RubricFactory)
    name = factory.Sequence(lambda n: 'criterion_{}'.format(n))  # pylint: disable=unnecessary-lambda
    label = factory.Sequence(lambda n: 'label_{}'.format(n))  # pylint: disable=unnecessary-lambda

    order_num = factory.Sequence(lambda n: n)

    prompt = 'This is a fake prompt.'


class CriterionOptionFactory(DjangoModelFactory):
    """ Create mock CriterionOption models. """
    class Meta:
        model = CriterionOption

    criterion = factory.SubFactory(CriterionFactory)

    order_num = factory.Sequence(lambda n: n)

    points = 4

    name = factory.Sequence(lambda n: 'option_{}'.format(n))  # pylint: disable=unnecessary-lambda
    label = factory.Sequence(lambda n: 'option__label_{}'.format(n))  # pylint: disable=unnecessary-lambda

    explanation = """The response makes 3-5 Monty Python references and at least one
                       original Star Wars trilogy reference. Do not select this option
                       if the author made any references to the second trilogy."""


class AssessmentFactory(DjangoModelFactory):
    """ Create mock Assessment models. """

    class Meta:
        model = Assessment

    submission_uuid = factory.Faker('sha1')
    rubric = factory.SubFactory(RubricFactory)

    scorer_id = 'test_scorer'
    score_type = 'PE'


class AssessmentPartFactory(DjangoModelFactory):
    """ Create mock AssessmentPart models. """
    class Meta:
        model = AssessmentPart

    assessment = factory.SubFactory(AssessmentFactory)

    criterion = factory.SubFactory(CriterionFactory)
    option = None

    feedback = 'This is my helpful feedback.'


class AssessmentFeedbackOptionFactory(DjangoModelFactory):
    """ Create mock AssessmentFeedbackOption models. """
    class Meta:
        model = AssessmentFeedbackOption

    text = factory.Sequence(lambda n: 'feedback_option_{}'.format(n))  # pylint: disable=unnecessary-lambda


class AssessmentFeedbackFactory(DjangoModelFactory):
    """ Create mock AssessmentFeedback models. """
    class Meta:
        model = AssessmentFeedback

    submission_uuid = factory.Faker('sha1')
    feedback_text = "Feedback Text!"

    @factory.post_generation
    def assessments(self, create, extracted, **kwargs):  # pylint: disable=unused-argument
        """ Handle the many-to-many relationship between AssessmentFeedback and Assessment. """
        if not create:
            return
        if extracted:
            for assessment in extracted:
                self.assessments.add(assessment)

    @factory.post_generation
    def options(self, create, extracted, **kwargs):  # pylint: disable=unused-argument
        """ Handle the many-to-many relationship between AssessmentFeedback and AssessmentFeedbackOption. """
        if not create:
            return
        if extracted:
            for option in extracted:
                self.options.add(option)
