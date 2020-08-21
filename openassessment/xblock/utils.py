"""
Grader ORA utils.
"""
from .job_sample_grader.job_sample_test_grader import TestGrader


# Map language name to be used in template code class
CODE_LANGUAGES = {
    'Python': 'language-python',
    'Java': 'language-java',
    'C++': 'language-cpp'
}


def get_code_language(language):
    """
    Create the prism js language tag for the given language.
    """
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

    try:
        return ((float(sample_correct + staff_correct)) / (staff_total + sample_total)) * 100
    except ZeroDivisionError:
        return 0


def grade_response(data, problem_name, add_staff_output=False):
    """
    Grade the response with per file test case feature.
    """
    data.update({'problem_name': problem_name})
    grader = TestGrader()
    output = grader.grade(data, add_staff_cases=add_staff_output)

    sample_output = output[0]
    if add_staff_output:
        # If staff output is required, send the original result as it is.
        return output
    return sample_output
