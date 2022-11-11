"""
Grader ORA utils.
"""
from openassessment.xblock.code_executor.factory import CODE_EXECUTOR_CONFIG_ID_MAP


# Map language name to be used in template code class
CODE_LANGUAGES = {
    'python': 'language-python',
    'java': 'language-java',
    'cpp': 'language-cpp',
    'javascript': 'language-nodejs'
}


def get_code_language(executor_id: str = ''):
    """
    Create the prism js language tag for the given language.
    """
    try:
        language = CODE_EXECUTOR_CONFIG_ID_MAP[executor_id].get(
            'language', executor_id.split(':')[0]
        )
        return CODE_LANGUAGES[language]
    except KeyError:
        return ""


def get_percentage(sample_submission, staff_submission):
    sample_correct = sample_submission.get('correct', 0)
    sample_total = sample_submission.get('total_tests', 0)

    staff_correct = staff_submission.get('correct', 0)
    staff_total = staff_submission.get('total_tests', 0)

    try:
        return ((float(sample_correct + staff_correct)) / (staff_total + sample_total)) * 100
    except ZeroDivisionError:
        return 0
