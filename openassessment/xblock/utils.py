
from __future__ import absolute_import


# Map language name to be used in template code class
CODE_LANGUAGES = {
    'Python': 'language-python',
    'Java': 'language-java',
    'C++': 'language-cpp'
}

OOP_PROBLEM_NAMES = ["call-center", "car-parking", "email-client"]


def get_code_language(source_code):
    """
    Employs the steps used in grader to check the code language.
    """
    language = source_code.split("\n")[0]
    language = ''.join([character for character in language if character.isalpha() or character == '+'])
    try:
        return CODE_LANGUAGES[language]
    except KeyError:
        return ""


def get_percentage(sample_submission, staff_submission):
    sample_correct = sample_submission['correct']
    sample_total = sample_submission['total_tests']

    staff_correct = staff_submission['correct']
    staff_total = staff_submission['total_tests']

    return (sample_correct + staff_correct) / (staff_total + sample_total)