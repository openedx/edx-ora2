"""Public interface managing the top results for the leaderboard.

The Leaderboard API exposes a single API which exposes the top answers for the submitted piece of assessment.

"""
import logging

from openassessment.assessment.models import Assessment
from submissions import api as sub_api

logger = logging.getLogger("openassessment.assessment.api.peer")

PEER_TYPE = "PE"


def get_leaderboard(number_of_top_scores=10):
    """
    Gets the top scores for a piece of assessment given the number of assessment required,
    and creates a anonymised array of dictionaries for the top results

    Kwargs:
        number_of_top_scores (int): The number of scores to return (default 10).

    Returns:
        An array of the highest submitted overall scores for the assessment. Returns
            an empty array if no submissions are completed.
    """
    topscores = []
    assessments = Assessment.objects.all()
    for assessment in assessments:
        sub = sub_api.get_submission_and_student(assessment.submission_uuid)
        score = assessment.points_earned
        text = sub['answer']['text']
        for i in range(int(number_of_top_scores)):
            if i < len(topscores):
                if int(topscores[i]['score']) < int(score):
                    topscores.insert(i, {'score': str(score), 'student_id': 'Anonymous', 'content': text})
                    break
            else:
                topscores.append({'score': str(score), 'student_id': 'Anonymous', 'content': text})
                break
    if len(topscores) > number_of_top_scores:
        topscores = topscores[0:number_of_top_scores]
    return topscores