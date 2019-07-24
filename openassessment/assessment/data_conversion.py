"""
Data Conversion utility methods for handling assessment data transformations.

"""
import six


def update_training_example_answer_format(answer):
    """
    For each training example update 'answer' to newer format.

    Args:
        answer unicode string or dict
    Returns:
        dict
    """
    if isinstance(answer, (str, six.text_type)):
        return {
            'parts': [
                {'text': answer}
            ]
        }

    return answer
