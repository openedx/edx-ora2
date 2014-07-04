"""Public interface managing the top results for the leaderboard.

The Leaderboard API exposes a single API which exposes the top answers for the submitted piece of assessment.

"""
from openassessment.assessment.models import Assessment
from submissions import api as sub_api

def get_leaderboard(submission_uuid, number_of_top_scores=10, display_student_ids=False):
    """
    Gets the top scores for a piece of assessment given the number of assessment required,
    and creates a anonymised array of dictionaries for the top results

    Args:
        workflow_uuid (string): The workflow ID for the assessment item

    Kwargs:
        number_of_top_scores (int): The number of scores to return (default 10).
        display_student_ids (Bool): Whether to display real student IDs

    Returns:
        An array of the highest submitted overall scores for the assessment. Returns
            an empty array if no submissions are completed.
    """
    topscores = []

    student_assessment = Assessment.objects.filter(submission_uuid=submission_uuid)
    if len(student_assessment) == 0:
        return topscores

    assessments = Assessment.objects.filter(rubric=student_assessment[0].rubric)
    for assessment in assessments:

        sub = sub_api.get_submission_and_student(assessment.submission_uuid)
        print sub
        score = assessment.points_earned
        text = sub['answer']
        if 'text' in sub['answer']:
            text = sub['answer']['text']
        for i in range(int(number_of_top_scores)):
            student_id = 'Anonymous'
            if display_student_ids:
                student_id = sub['student_item']['student_id']
            if i < len(topscores):
                if int(topscores[i]['score']) < int(score):
                    topscores.insert(i, {'score': str(score), 'student_id': student_id, 'content': text})
                    break
            else:
                topscores.append({'score': str(score), 'student_id': student_id, 'content': text})
                break
    if len(topscores) > number_of_top_scores:
        topscores = topscores[0:number_of_top_scores]
    return topscores