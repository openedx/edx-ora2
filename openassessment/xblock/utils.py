
from __future__ import absolute_import


# Map language name to be used in template code class
CODE_LANGUAGES = {
    'Python': 'language-python',
    'Java': 'language-java',
    'C++': 'language-cpp'
}


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
