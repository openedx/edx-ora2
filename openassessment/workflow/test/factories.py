""" Factories for testing workflow models """

import factory
from factory.django import DjangoModelFactory

from openassessment.workflow.models import TeamAssessmentWorkflow, AssessmentWorkflowStep


class TeamAssessmentWorkflowFactory(DjangoModelFactory):
    """ Create mock TeamAssessmentWorkflow models. """
    class Meta:
        model = TeamAssessmentWorkflow

    team_submission_uuid = factory.Faker('sha1')
    submission_uuid = factory.Faker('sha1')
    course_id = factory.Sequence(lambda n: 'default_course_{}'.format(n))  # pylint: disable=unnecessary-lambda
    item_id = factory.Sequence(lambda n: 'default_course_{}'.format(n))  # pylint: disable=unnecessary-lambda


class AssessmentWorkflowStepFactory(DjangoModelFactory):
    """ Create mock AssessmentWorkflowStep models. """
    class Meta:
        model = AssessmentWorkflowStep

    workflow = factory.SubFactory(TeamAssessmentWorkflowFactory)
    name = 'staff'
    order_num = 1
