"""
Data Conversion utility methods for handling assessment data transformations.

"""
import json


def update_training_example_answer_format(answer):
    """
    For each training example update 'answer' to newer format.

    Args:
        assessments (list): list of assessments
    Returns:
        list of dict
    """
    if isinstance(answer, unicode) or isinstance(answer, str):
        return {
            'parts': [
                {'text': answer}
            ]
        }

    return answer