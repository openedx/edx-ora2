"""Public interface managing the workflow for peer assessments.

The Peer Assessment Workflow API exposes all public actions required to complete
the workflow for a given submission.

"""
import logging
from django.utils import timezone
from django.db import DatabaseError, IntegrityError
from dogapi import dog_stats_api

from openassessment.assessment.models import (
    Assessment, AssessmentFeedback, AssessmentPart,
    InvalidOptionSelection, PeerWorkflow, PeerWorkflowItem,
)
from openassessment.assessment.serializers import (
    AssessmentSerializer, AssessmentFeedbackSerializer, RubricSerializer,
    full_assessment_dict, rubric_from_dict, serialize_assessments,
)
from openassessment.assessment.errors import (
    PeerAssessmentRequestError, PeerAssessmentWorkflowError, PeerAssessmentInternalError
)
from submissions import api as sub_api

logger = logging.getLogger("openassessment.assessment.api.peer")

PEER_TYPE = "PE"


def get_leaderboard():

    topscores = []

    assessments = Assessment.objects.all()
    for assessment in assessments:
        sub = sub_api.get_submission_and_student(assessment.submission_uuid)
        score = assessment.points_earned
        text = sub['answer']['text']
        for i in range(10):
            if i < len(topscores):
                if int(topscores[i]['score']) < int(score):
                    topscores.insert(i, {'score': str(score), 'student_id': 'Anonymous', 'content': text})
                    break
            else:
                topscores.append({'score': str(score), 'student_id': 'Anonymous', 'content': text})
                break
    return topscores