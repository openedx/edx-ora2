"""Default data initializations for the XBlock, with formatting preserved."""
# -*- coding: utf-8 -*-
# pylint: disable=line-too-long

from django.utils.translation import ugettext_lazy


DEFAULT_PROMPT = ugettext_lazy("""
    Censorship in the Libraries

    'All of us can think of a book that we hope none of our children or any other children have taken off the shelf. But if I have the right to remove that book from the shelf -- that work I abhor -- then you also have exactly the same right and so does everyone else. And then we have no books left on the shelf for any of us.' --Katherine Paterson, Author

    Write a persuasive essay to a newspaper reflecting your views on censorship in libraries. Do you believe that certain materials, such as books, music, movies, magazines, etc., should be removed from the shelves if they are found offensive? Support your position with convincing arguments from your own experience, observations, and/or reading.

    Read for conciseness, clarity of thought, and form.
  """)

DEFAULT_RUBRIC_CRITERIA = [
    {
        'name': ugettext_lazy("Ideas"),
        'label': ugettext_lazy("Ideas"),
        'prompt': ugettext_lazy("Determine if there is a unifying theme or main idea."),
        'order_num': 0,
        'feedback': ugettext_lazy('optional'),
        'options': [
            {
                'order_num': 0, 'points': 0, 'name': ugettext_lazy('Poor'), 'label': ugettext_lazy('Poor'),
                'explanation': ugettext_lazy("""Difficult for the reader to discern the main idea.  Too brief or too repetitive to establish or maintain a focus.""")
            },
            {
                'order_num': 1, 'points': 3, 'name': ugettext_lazy('Fair'), 'label': ugettext_lazy('Fair'),
                'explanation': ugettext_lazy("""Presents a unifying theme or main idea, but may include minor tangents.  Stays somewhat focused on topic and task.""")
            },
            {
                'order_num': 2, 'points': 5, 'name': ugettext_lazy('Good'), 'label': ugettext_lazy('Good'),
                'explanation': ugettext_lazy("""Presents a unifying theme or main idea without going off on tangents.  Stays completely focused on topic and task.""")
            },
        ],
    },
    {
        'name': ugettext_lazy("Content"),
        'label': ugettext_lazy("Content"),
        'prompt': ugettext_lazy("Assess the content of the submission"),
        'order_num': 1,
        'options': [
            {
                'order_num': 0, 'points': 0, 'name': ugettext_lazy('Poor'), 'label': ugettext_lazy('Poor'),
                'explanation': ugettext_lazy("""Includes little information with few or no details or unrelated details.  Unsuccessful in attempts to explore any facets of the topic.""")
            },
            {
                'order_num': 1, 'points': 1, 'name': ugettext_lazy('Fair'), 'label': ugettext_lazy('Fair'),
                'explanation': ugettext_lazy("""Includes little information and few or no details.  Explores only one or two facets of the topic.""")
            },
            {
                'order_num': 2, 'points': 3, 'name': ugettext_lazy('Good'), 'label': ugettext_lazy('Good'),
                'explanation': ugettext_lazy("""Includes sufficient information and supporting details. (Details may not be fully developed; ideas may be listed.)  Explores some facets of the topic.""")
            },
            {
                'order_num': 3, 'points': 3, 'name': ugettext_lazy('Excellent'), 'label': ugettext_lazy('Excellent'),
                'explanation': ugettext_lazy("""Includes in-depth information and exceptional supporting details that are fully developed.  Explores all facets of the topic.""")
            },
        ],
    },
]

# The rubric's feedback prompt is a set of instructions letting the student
# know they can provide additional free form feedback in their assessment.
DEFAULT_RUBRIC_FEEDBACK_PROMPT = ugettext_lazy("""
(Optional) What aspects of this response stood out to you? What did it do well? How could it be improved?
""")


# The rubric's feedback text is the default text displayed and used as
# the student's response to the feedback prompt
DEFAULT_RUBRIC_FEEDBACK_TEXT = ugettext_lazy("""
I think that this response...
""")

DEFAULT_EXAMPLE_ANSWER = (
    ugettext_lazy("Replace this text with your own sample response for this assignment. "
    "Then, under Response Score to the right, select an option for each criterion. "
    "Learners practice performing peer assessments by assessing this response and comparing "
    "the options that they select in the rubric with the options that you specified.")
)

DEFAULT_EXAMPLE_ANSWER_2 = (
    ugettext_lazy("Replace this text with another sample response, "
    "and then specify the options that you would select for this response.")
)

DEFAULT_STUDENT_TRAINING = {
    "name": ugettext_lazy("student-training"),
    "start": None,
    "due": None,
    "examples": [
        {
            "answer": DEFAULT_EXAMPLE_ANSWER,
            "options_selected": [
                {
                    "criterion": ugettext_lazy("Ideas"),
                    "option": ugettext_lazy("Fair")
                },
                {
                    "criterion": ugettext_lazy("Content"),
                    "option": ugettext_lazy("Good")
                }
            ]
        },
        {
            "answer": DEFAULT_EXAMPLE_ANSWER_2,
            "options_selected": [
                {
                    "criterion": ugettext_lazy("Ideas"),
                    "option": ugettext_lazy("Poor")
                },
                {
                    "criterion": ugettext_lazy("Content"),
                    "option": ugettext_lazy("Good")
                }
            ]
        }
    ]
}

DEFAULT_START = "2001-01-01T00:00"
DEFAULT_DUE = "2029-01-01T00:00"

# The Default Peer Assessment is created as an example of how this XBlock can be
# configured. If no configuration is specified, this is the default assessment
# module(s) associated with the XBlock.
DEFAULT_PEER_ASSESSMENT = {
    "name": ugettext_lazy("peer-assessment"),
    "start": DEFAULT_START,
    "due": DEFAULT_DUE,
    "must_grade": 5,
    "must_be_graded_by": 3,
}

DEFAULT_SELF_ASSESSMENT = {
    "name": ugettext_lazy("self-assessment"),
    "start": DEFAULT_START,
    "due": DEFAULT_DUE,
}

DEFAULT_STAFF_ASSESSMENT = {
    "name": ugettext_lazy("staff-assessment"),
    "start": DEFAULT_START,
    "due": DEFAULT_DUE,
    "required": False,
}

DEFAULT_ASSESSMENT_MODULES = [
    DEFAULT_STUDENT_TRAINING,
    DEFAULT_PEER_ASSESSMENT,
    DEFAULT_SELF_ASSESSMENT,
    DEFAULT_STAFF_ASSESSMENT,
]

DEFAULT_EDITOR_ASSESSMENTS_ORDER = [
    ugettext_lazy("student-training"),
    ugettext_lazy("peer-assessment"),
    ugettext_lazy("self-assessment"),
    ugettext_lazy("staff-assessment"),
]
