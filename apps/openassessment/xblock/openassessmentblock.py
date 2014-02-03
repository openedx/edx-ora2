"""An XBlock where students can read a question and compose their response"""

from HTMLParser import HTMLParser 
import pkg_resources

from django.utils.html import escape as util_escape
from mako.template import Template

from submissions import api

from xblock.core import XBlock
from xblock.fields import Scope, String
from xblock.fragment import Fragment


mako_default_filters = ['unicode', 'h', 'trim']


def escape(html_string):
    """Escape HTML entities in a string, returning an uninterpretable string."""
    return util_escape(html_string)

def unescape(encoded_html_string):
    """Unescape HTML entities from a string, returning values to give user."""
    return HTMLParser().unescape(encoded_html_string)


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
        frag = Fragment(html.render_unicode(xblock_trace=trace, question=unescape(self.prompt)))
        frag.add_css(load("static/css/openassessment.css"))
        frag.add_javascript(load("static/js/src/openassessment.js"))
        frag.initialize_js('OpenAssessmentBlock')
        return frag

    @XBlock.json_handler
    def submit(self, data, suffix=''):
        """
        Place the submission text into Openassessment system
        """
        errors = {'ENOSUB', 'API submission is unrequested',
                  'ENODATA', 'API returned an empty response',
                  'EBADFORM', 'API Submission Request Error',
                  'EUNKNOWN', 'API returned unclassified exception',
                 }
        status = False
        status_tag = 'ENOSUB'
        status_text = None
        student_sub = data['submission']
        item_id, student_id = self._get_xblock_trace()
        student_item_dict = dict(
            student_id=student_id,
            item_id=item_id,
            course_id=self.course_id,
            item_type='openassessment'      # XXX: Is this the tag we want? Why?
        )
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
        status_text = status_text if status_text else errors[status_tag]
        return (status, status_tag, status_text)

    # Arbitrary attributes can be defined on the 
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
#        prompt_string = """<h3>Censorship in the Libraries</h3>
#<p>'All of us can think of a book that we hope none of our children or any other children have taken off the 
#shelf. But if I have the right to remove that book from the shelf -- that work I abhor -- then you also have
#exactly the same right and so does everyone else. And then we have no books left on the shelf for any of
#us.' --Katherine Paterson, Author</p>
#<p>Write a persuasive essay to a newspaper reflecting your views on censorship in libraries. Do you believe
#that certain materials, such as books, music, movies, magazines, etc., should be removed from the shelves if
#they are found offensive? Support your position with convincing arguments from your own experience,
#observations, and/or reading.</p>"""
        prompt_string = "This is my prompt. There are many like it, but this one is mine."
        return [
            ("OpenAssessmentBlock",
             """<vertical_demo>
                <openassessment prompt="{prompt_string}" />
                </vertical_demo>
             """.format(prompt_string=prompt_string)),
        ]

#         <h3>Censorship in the Libraries</h3>
#
#        <p>'All of us can think of a book that we hope none of our children or any other children have taken off the shelf. But if I have the right to remove that book from the shelf -- that work I abhor -- then you also have exactly the same right and so does everyone else. And then we have no books left on the shelf for any of us.' --Katherine Paterson, Author
#        </p>
#
#        <p>
#        Write a persuasive essay to a newspaper reflecting your views on censorship in libraries. Do you believe that certain materials, such as books, music, movies, magazines, etc., should be removed from the shelves if they are found offensive? Support your position with convincing arguments from your own experience, observations, and/or reading.
#        </p>
