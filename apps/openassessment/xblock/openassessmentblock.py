"""An XBlock where students can read a question and compose their response"""

import datetime
import pkg_resources

from django.template.context import Context
from django.template.loader import get_template
from webob import Response

from xblock.core import XBlock
from xblock.fields import List, Scope, String
from xblock.fragment import Fragment

from middleware.request_id import get_request
from openassessment.xblock.peer_assessment_mixin import PeerAssessmentMixin
from openassessment.xblock.self_assessment_mixin import SelfAssessmentMixin
from openassessment.xblock.submission_mixin import SubmissionMixin

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

UI_MODELS = {
    "submission": {
        "assessment_type": "submission",
        "name": "submission",
        "class_id": "openassessment__response",
        "navigation_text": "Your response to this problem",
        "title": "Your Response"
    },
    "peer-assessment": {
        "assessment_type": "peer-assessment",
        "name": "peer-assessment",
        "class_id": "openassessment__peer-assessment",
        "navigation_text": "Your assessment(s) of peer responses",
        "title": "Assess Peers' Responses"
    },
    "self-assessment": {
        "assessment_type": "self-assessment",
        "name": "self-assessment",
        "class_id": "openassessment__self-assessment",
        "navigation_text": "Your assessment of your response",
        "title": "Assess Your Response"
    }
}

"""
The Default Peer Assessment is created as an example of how this XBlock can be
configured. If no configuration is specified, this is the default assessment
module(s) associated with the XBlock.
"""
DEFAULT_PEER_ASSESSMENT = {
    "assessment_type": "peer-assessment",
    "name": "peer-assessment",
    "start_datetime": datetime.datetime.now().isoformat(),
    "must_grade": 5,
    "must_be_graded_by": 3,
}

DEFAULT_ASSESSMENT_MODULES = [
    DEFAULT_PEER_ASSESSMENT,
]

# Used to parse datetime strings from the XML configuration.
TIME_PARSE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def load(path):
    """Handy helper for getting resources from our kit."""
    data = pkg_resources.resource_string(__name__, path)
    return data.decode("utf8")


class OpenAssessmentBlock(XBlock, SubmissionMixin, PeerAssessmentMixin, SelfAssessmentMixin):
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

    def get_xblock_trace(self):
        """Uniquely identify this XBlock by context.

        Every XBlock has a scope_ids, which is a NamedTuple describing
        important contextual information. Per @nedbat, the usage_id attribute
        uniquely identifies this block in this course, and the user_id uniquely
        identifies this student. With the two of them, we can trace all the
        interactions emanating from this interaction."""
        return (self.scope_ids.usage_id, self.scope_ids.user_id)

    def get_student_item_dict(self):
        """Create a student_item_dict from our surrounding context.

        See also: submissions.api for details.

        Returns:
            (dict): The student item associated with this XBlock instance. This
                includes the student id, item id, and course id.
        """
        item_id, student_id = self.get_xblock_trace()
        student_item_dict = dict(
            student_id=student_id,
            item_id=item_id,
            course_id=self.course_id,
            item_type='openassessment'      # XXX: Is this the tag we want? Why?
        )
        return student_item_dict

    def student_view(self, context=None):
        """The main view of OpenAssessmentBlock, displayed when viewing courses.

        The main view which displays the general layout for Open Ended
        Assessment Questions. The contents of the XBlock are determined
        dynamically based on the assessment workflow configured by the author.

        Args:
            context: Not used for this view.

        Returns:
            (Fragment): The HTML Fragment for this XBlock, which determines the
            general frame of the Open Ended Assessment Question.
        """
        trace = self.get_xblock_trace()
        token = getattr(get_request(), 'META', {}).get('HTTP_X_EDX_LOG_TOKEN', None)
        ui_models = self._create_ui_models()
        grade_state = self.get_grade_state()
        # All data we intend to pass to the front end.
        context_dict = {
            "xblock_trace": trace,
            "title": self.title,
            "question": self.prompt,
            "rubric_instructions": self.rubric_instructions,
            "rubric_criteria": self.rubric_criteria,
            "rubric_assessments": ui_models,
            "grade_state": grade_state,
            "log_token": token,
        }

        template = get_template("openassessmentblock/oa_base.html")
        context = Context(context_dict)
        frag = Fragment(template.render(context))
        frag.add_css(load("static/css/openassessment.css"))
        frag.add_javascript(load("static/js/src/oa_base.js"))
        frag.initialize_js('OpenAssessmentBlock')
        return frag

    def _create_ui_models(self):
        """Combine UI attributes and XBlock configuration into a UI model.

        This method takes all configuration for this XBlock instance and appends
        UI attributes to create a UI Model for rendering all assessment modules.
        This allows a clean separation of static UI attributes from persistent
        XBlock configuration.

        """
        ui_models = [UI_MODELS["submission"]]
        for assessment in self.rubric_assessments:
            ui_model = UI_MODELS[assessment["assessment_type"]]
            ui_models.append(dict(assessment, **ui_model))
        return ui_models

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench.

        These scenarios are only intended to be used for Workbench XBlock
        Development.

        """
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
        """Determines how the XBlock is rendered for editing in Studio.

        Displays the section where Editing can occur within Studio to modify
        this XBlock instance.

        Args:
            context: Not actively used for this view.

        Returns:
            (Fragment): An HTML fragment for editing the configuration of this
                XBlock.

        """
        return Fragment(u"<div>Edit the XBlock.</div>")

    @classmethod
    def parse_xml(cls, node, runtime, keys, id_generator):
        """Instantiate XBlock object from runtime XML definition.

        Inherited by XBlock core.

        """
        def unknown_handler(block, child):
            """Recursively embed xblocks for nodes we don't recognize"""
            block.runtime.add_node_as_child(block, child, id_generator)
        block = runtime.construct_xblock_from_class(cls, keys)

        sparser = ScenarioParser(block, node, unknown_handler)
        block = sparser.parse()
        return block

    def get_grade_state(self):
        # TODO: Placeholder for workflow state.

        grade_state = {
            "style_class": "is--incomplete",
            "value": "Incomplete",
            "title": "Your Grade:",
            "message": "You have not started this problem",
        }
        return grade_state

    def render_assessment(self, path, context_dict=None):
        """Render an Assessment Module's HTML

        Given the name of an assessment module, find it in the list of
        configured modules, and ask for its rendered HTML.

        Args:
            path (str): The path to the template used to render this HTML
                section.
            context_dict (dict): A dictionary of context variables used to
                populate this HTML section.

        Returns:
            (Response): A Response Object with the generated HTML fragment. This
                is intended for AJAX calls to load dynamically into a larger
                document.
        """
        if not context_dict:
            context_dict = {}

        context_dict["xblock_trace"] = self.get_xblock_trace()

        if self.start_datetime:
            start = datetime.datetime.strptime(self.start_datetime, TIME_PARSE_FORMAT)
            context_dict["formatted_start_date"] = start.strftime("%A, %B %d, %Y")
            context_dict["formatted_start_datetime"] = start.strftime("%A, %B %d, %Y %X")
        if self.due_datetime:
            due = datetime.datetime.strptime(self.due_datetime, TIME_PARSE_FORMAT)
            context_dict["formatted_due_date"] = due.strftime("%A, %B %d, %Y")
            context_dict["formatted_due_datetime"] = due.strftime("%A, %B %d, %Y %X")

        template = get_template(path)
        context = Context(context_dict)
        return Response(template.render(context), content_type='application/html', charset='UTF-8')

    def is_open(self):
        """Checks if the question is open.

        Determines if the start date has occurred and the end date has not
        passed.

        Returns:
            (tuple): True if the question is open, False if not. If False,
                specifies if the "start" date or "due" date is the closing
                factor.

        Examples:
            >>> is_open()
            False, "due"

        """
        # Is the question closed?
        if self.start_datetime:
            start = datetime.datetime.strptime(self.start_datetime, TIME_PARSE_FORMAT)
            if start > datetime.datetime.utcnow():
                return False, "start"
        if self.due_datetime:
            due = datetime.datetime.strptime(self.due_datetime, TIME_PARSE_FORMAT)
            if due < datetime.datetime.utcnow():
                return False, "due"
        return True, None
