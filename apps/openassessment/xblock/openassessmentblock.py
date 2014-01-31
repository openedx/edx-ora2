"""An XBlock where students can read a question and compose their response"""

import pkg_resources

from mako.template import Template

from submissions import api

from xblock.core import XBlock
from xblock.fields import Scope, String
from xblock.fragment import Fragment


mako_default_filters = ['unicode', 'h', 'trim']


class OpenAssessmentBlock(XBlock):
    """
    Displays a question and gives an area where students can compose a response.
    """

    prompt = String(
        default=u"This prompt is unconfigured. Perhaps you could enter some text telling us a little about yourself?",
        scope=Scope.content,
        help="A prompt to display to a student",
    )
    course_id = String(
        default=u"TestCourse",
        scope=Scope.content,
        help="The course_id associated with this prompt (until we can get it from runtime).",
    )


    def _get_xblock_trace(self):
        """Uniquely identify this xblock by context.

        Every XBlock has a scope_ids, which is a NamedTuple describing
        important contextual information. Per @nedbat, the usage_id attribute
        uniquely identifies this block in this course, and the user_id uniquely
        identifies this student. With the two of them, we can trace all the
        interactions emenating from this interaction.

        Useful for logging, debugging, and uniqueification."""
        return (self.scope_ids.usage_id, self.scope_ids.user_id)

    def student_view(self, context=None):
        """
        The main view of OpenAssessmentBlock, displayed when viewing courses.
        """
        def load(path):
            """Handy helper for getting resources from our kit."""
            data = pkg_resources.resource_string(__name__, path)
            return data.decode("utf8")

        trace = self._get_xblock_trace()
        html = Template(load("static/html/openassessment.html"),
                        default_filters=mako_default_filters,
                        input_encoding='utf-8',
                       )
        frag = Fragment(html.render_unicode(xblock_trace=trace, question=self.prompt))
        frag.add_css(load("static/css/openassessment.css"))
        frag.add_javascript(load("static/js/src/openassessment.js"))
        frag.initialize_js('OpenAssessmentBlock')
        return frag

    @XBlock.json_handler
    def submit(self, data, suffix=''):
        """
        Place the submission text into Openassessment system
        """
        student_sub = data['submission']
        item_id, student_id = self._get_xblock_trace()
        student_item_dict = dict(
            student_id=student_id,
            item_id=item_id,
            course_id=self.course_id,
            item_type='openassessment'      # Is this the tag we want? Why?
        )
        status = False
        try:
            response = api.create_submission(student_item_dict, student_sub)
            status = True if response else False
        except api.SubmissionError:
            status = False
        return status

    # Arbitrary attributes can be defined on the 
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("OpenAssessmentBlock",
             """<vertical_demo>
                <openassessment prompt="This is my prompt. There are many like it, but this one is mine." />
                </vertical_demo>
             """),
        ]

#         <h3>Censorship in the Libraries</h3>
#
#        <p>'All of us can think of a book that we hope none of our children or any other children have taken off the shelf. But if I have the right to remove that book from the shelf -- that work I abhor -- then you also have exactly the same right and so does everyone else. And then we have no books left on the shelf for any of us.' --Katherine Paterson, Author
#        </p>
#
#        <p>
#        Write a persuasive essay to a newspaper reflecting your views on censorship in libraries. Do you believe that certain materials, such as books, music, movies, magazines, etc., should be removed from the shelves if they are found offensive? Support your position with convincing arguments from your own experience, observations, and/or reading.
#        </p>
