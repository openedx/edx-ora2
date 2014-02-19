"""An XBlock where students can read a question and compose their response"""

from django.template.context import Context
import pkg_resources

from django.template.loader import get_template

import datetime

from xblock.core import XBlock
from xblock.fields import List, Scope, String
from xblock.fragment import Fragment
from openassessment.xblock.peer_assessment import PeerAssessment
from submissions.api import SubmissionRequestError
from submissions import api

from scenario_parser import ScenarioParser

DEFAULT_PROMPT = """
    Censorship in the Libraries

    'All of us can think of a book that we hope none of our children or any
    other children have taken off the shelf. But if I have the right to remove
    that book from the shelf -- that work I abhor -- then you also have exactly
    the same right and so does everyone else. And then we have no books left on
    the shelf for any of us.' --Katherine Paterson, Author

    Write a persuasive essay to a newspaper reflecting your views on censorship
    in libraries. Do you believe that certain materials, such as books, music,
    movies, magazines, etc., should be removed from the shelves if they are
    found offensive? Support your position with convincing arguments from your
    own experience, observations, and/or reading.
"""

DEFAULT_RUBRIC_INSTRUCTIONS = "Read for conciseness, clarity of thought, and form."

DEFAULT_RUBRIC_CRITERIA = [
    {
        'name': "Ideas",
        'instructions': "Determine if there is a unifying theme or main idea.",
        'total_value': 5,
        'options': [
            (0, "Poor", """Difficult for the reader to discern the main idea.
                Too brief or too repetitive to establish or maintain a focus.""",),
            (3, "Fair", """Presents a unifying theme or main idea, but may
                include minor tangents.  Stays somewhat focused on topic and
                task.""",),
            (5, "Good", """Presents a unifying theme or main idea without going
                off on tangents.  Stays completely focused on topic and task.""",),
        ],
    },
    {
        'name': "Content",
        'instructions': "Assess the content of the submission",
        'total_value': 5,
        'options': [
            (0, "Poor", """Includes little information with few or no details or
                unrelated details.  Unsuccessful in attempts to explore any
                facets of the topic.""",),
            (1, "Fair", """Includes little information and few or no details.
                Explores only one or two facets of the topic.""",),
            (3, "Good", """Includes sufficient information and supporting
                details. (Details may not be fully developed; ideas may be
                listed.)  Explores some facets of the topic.""",),
            (5, "Excellent", """Includes in-depth information and exceptional
                supporting details that are fully developed.  Explores all
                facets of the topic.""",),
        ],
    },
    {
        'name': "Organization",
        'instructions': "Determine if the submission is well organized.",
        'total_value': 2,
        'options': [
            (0, "Poor", """Ideas organized illogically, transitions weak, and
                response difficult to follow.""",),
            (1, "Fair", """Attempts to logically organize ideas.  Attempts to
                progress in an order that enhances meaning, and demonstrates use
                of transitions.""",),
            (2, "Good", """Ideas organized logically.  Progresses in an order
                that enhances meaning.  Includes smooth transitions.""",),
        ],
    },
    {
        'name': "Style",
        'instructions': "Read for style.",
        'total_value': 2,
        'options': [
            (0, "Poor", """Contains limited vocabulary, with many words used
                incorrectly.  Demonstrates problems with sentence patterns.""",),
            (1, "Fair", """Contains basic vocabulary, with words that are
                predictable and common.  Contains mostly simple sentences
                (although there may be an attempt at more varied sentence
                patterns).""",),
            (2, "Good", """Includes vocabulary to make explanations detailed and
                precise.  Includes varied sentence patterns, including complex
                sentences.""",),
        ],
    },
    {
        'name': "Voice",
        'instructions': "Read for style.",
        'total_value': 2,
        'options': [
            (0, "Poor", """Demonstrates language and tone that may be
                inappropriate to task and reader.""",),
            (1, "Fair", """Demonstrates an attempt to adjust language and tone
                to task and reader.""",),
            (2, "Good", """Demonstrates effective adjustment of language and
                tone to task and reader.""",),
        ],
    }
]

DEFAULT_PEER_ASSESSMENT = PeerAssessment()
DEFAULT_PEER_ASSESSMENT.name = "peer-assessment"
DEFAULT_PEER_ASSESSMENT.start_datetime = datetime.datetime.now().isoformat()
DEFAULT_PEER_ASSESSMENT.must_grade = 5
DEFAULT_PEER_ASSESSMENT.must_be_graded_by = 3

DEFAULT_ASSESSMENT_MODULES = [
    DEFAULT_PEER_ASSESSMENT,
]


def load(path):
    """Handy helper for getting resources from our kit."""
    data = pkg_resources.resource_string(__name__, path)
    return data.decode("utf8")


class OpenAssessmentBlock(XBlock):
    """Displays a question and gives an area where students can compose a response."""

    start_datetime = String(
        default=datetime.datetime.now().isoformat(),
        scope=Scope.content,
        help="ISO-8601 formatted string representing the start date of this assignment."
    )
    due_datetime = String(
        default=None,
        scope=Scope.content,
        help="ISO-8601 formatted string representing the end date of this assignment."
    )

    title = String(
        default="",
        scope=Scope.content,
        help="A title to display to a student (plain text)."
    )
    prompt = String(
        default=DEFAULT_PROMPT,
        scope=Scope.content,
        help="A prompt to display to a student (plain text)."
    )
    rubric = List(
        default=[],
        scope=Scope.content,
        help="Instructions and criteria for students giving feedback."
    )
    rubric_instructions = String(
        default=DEFAULT_RUBRIC_INSTRUCTIONS,
        scope=Scope.content,
        help="Instructions for self and peer assessment."
    )
    rubric_criteria = List(
        default=DEFAULT_RUBRIC_CRITERIA,
        scope=Scope.content,
        help="The different parts of grading for students giving feedback."
    )
    rubric_assessments = List(
        default=DEFAULT_ASSESSMENT_MODULES,
        scope=Scope.content,
        help="The requested set of assessments and the order in which to apply them."
    )
    course_id = String(
        default=u"TestCourse",
        scope=Scope.content,
        help="The course_id associated with this prompt (until we can get it from runtime).",
    )

    submit_errors = {     # Reported to user sometimes, and useful in tests
              'ENOSUB':   'API submission is unrequested',
              'ENODATA':  'API returned an empty response',
              'EBADFORM': 'API Submission Request Error',
              'EUNKNOWN': 'API returned unclassified exception',
    }

    def _get_xblock_trace(self):
        """Uniquely identify this xblock by context.

        Every XBlock has a scope_ids, which is a NamedTuple describing
        important contextual information. Per @nedbat, the usage_id attribute
        uniquely identifies this block in this course, and the user_id uniquely
        identifies this student. With the two of them, we can trace all the
        interactions emanating from this interaction.

        Useful for logging, debugging, and uniqueification."""
        return self.scope_ids.usage_id, self.scope_ids.user_id

    def _get_student_item_dict(self):
        """Create a student_item_dict from our surrounding context.

        See also: submissions.api for details.
        """
        item_id, student_id = self._get_xblock_trace()
        student_item_dict = dict(
            student_id=student_id,
            item_id=item_id,
            course_id=self.course_id,
            item_type='openassessment'      # XXX: Is this the tag we want? Why?
        )
        return student_item_dict

    def student_view(self, context=None):
        """The main view of OpenAssessmentBlock, displayed when viewing courses.
        """

        trace = self._get_xblock_trace()
        student_item_dict = self._get_student_item_dict()

        grade_state = self._get_grade_state()
        # All data we intend to pass to the front end.
        context_dict = {
            "xblock_trace": trace,
            "title": self.title,
            "question": self.prompt,
            "rubric_instructions": self.rubric_instructions,
            "rubric_criteria": self.rubric_criteria,
            "rubric_assessments": [assessment.create_ui_model() for assessment in self.rubric_assessments],
            "grade_state": grade_state,
        }

        try:
            previous_submissions = api.get_submissions(student_item_dict)
        except SubmissionRequestError:
            previous_submissions = []

        peer_module = self._get_assessment_module('peer-assessment')
        peer_assessment = peer_module.get_peer_submission(student_item_dict)
        if previous_submissions and peer_assessment:  # XXX: until workflow better, move on w/ prev submit
            template = get_template("static/html/oa_base.html")
            context = Context(context_dict)
            frag = Fragment(template.render(context))
            frag.add_css(load("static/css/openassessment.css"))
            frag.add_javascript(load("static/js/src/oa_assessment.js"))
            frag.initialize_js('OpenAssessmentBlock')
        elif previous_submissions:
            return Fragment(u"<div>There are no submissions to review.</div>")
        else:                     # XXX: until workflow better, submit until submitted
            template = get_template("static/html/oa_base.html")
            context = Context(context_dict)
            frag = Fragment(template.render(context))
            frag.add_css(load("static/css/openassessment.css"))
            frag.add_javascript(load("static/js/src/oa_submission.js"))
            frag.initialize_js('OpenAssessmentBlock')
        return frag

    @XBlock.json_handler
    def assess(self, data, suffix=''):
        # TODO Pass name through the handler.
        assessment = self._get_assessment_module('peer-assessment')
        if assessment:
            assessment.assess(
                self._get_student_item_dict(),
                self.rubric_criteria,
                data
            )

    def _get_assessment_module(self, name):
        """Get a configured assessment module by name.
        """
        for assessment in self.rubric_assessments:
            if assessment.name == name:
                return assessment

    @XBlock.json_handler
    def submit(self, data, suffix=''):
        """
        Place the submission text into Openassessment system
        """
        status = False
        status_tag = 'ENOSUB'
        status_text = None
        student_sub = data['submission']
        student_item_dict = self._get_student_item_dict()
        try:
            status_tag = 'ENODATA'
            response = api.create_submission(student_item_dict, student_sub)
            if response:
                status = True
                status_tag = response.get('student_item')
                status_text = response.get('attempt_number')
        except api.SubmissionRequestError, e:
            status_tag = 'EBADFORM'
            status_text = unicode(e.field_errors)
        except api.SubmissionError:
            status_tag = 'EUNKNOWN'
        # relies on success being orthogonal to errors
        status_text = status_text if status_text else self.submit_errors[status_tag]
        return status, status_tag, status_text

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            (
                "OpenAssessmentBlock Poverty Rubric",
                load('static/xml/poverty_rubric_example.xml')
            ),
            (
                "OpenAssessmentBlock Censorship Rubric",
                load('static/xml/censorship_rubric_example.xml')
            ),
        ]

    @staticmethod
    def studio_view(context=None):
        return Fragment(u"<div>Edit the XBlock.</div>")

    @classmethod
    def parse_xml(cls, node, runtime, keys, id_generator):
        """Instantiate xblock object from runtime XML definition."""
        def unknown_handler(block, child):
            """Recursively embed xblocks for nodes we don't recognize"""
            block.runtime.add_node_as_child(block, child, id_generator)
        block = runtime.construct_xblock_from_class(cls, keys)

        sparser = ScenarioParser(block, node, unknown_handler)
        block = sparser.parse()
        return block

    def _get_grade_state(self):
        # TODO: Determine if we want to build out grade state right now.

        grade_state = {
            "style_class": "is--incomplete",
            "value": "Incomplete",
            "title": "Your Grade:",
            "message": "You have not started this problem",
        }
        return grade_state
