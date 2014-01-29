"""An XBlock where students can read a question and compose their response"""

import pkg_resources

from mako.template import Template

from xblock.core import XBlock
from xblock.fields import Scope, String
from xblock.fragment import Fragment


mako_default_filters = ['unicode', 'h', 'trim']


class openassessmentComposeXBlock(XBlock):
    """
    Displays a question and gives an area where students can compose a response.
    """

    question = String(default=u"Undefined question", scope=Scope.content, help="A question to display to a student")

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
        The primary view of the OpenassessmentComposeXBlock, shown to students
        when viewing courses.
        """
        def load(path):
            """Handy helper for getting resources from our kit."""
            data = pkg_resources.resource_string(__name__, path)
            return data.decode("utf8")

        trace = self._get_xblock_trace()
        html = Template(load("static/html/openassessment_compose.html"),
                        default_filters=mako_default_filters,
                        input_encoding='utf-8',
                       )
        frag = Fragment(html.render_unicode(xblock_trace=trace, question=self.question))
        frag.add_css(load("static/css/openassessment_compose.css"))
        # XXX: I'm sure there's a more socially acceptable way to get our values
        #      into the js. But once we've invoked mako it's so tempting....
        #frag.add_javascript(Template(load("static/js/src/openassessment_compose.js"), 
        #                             default_filters=mako_default_filters, 
        #                             output_encoding='utf-8'
        #                            ).render(xblock_trace=trace))
        frag.add_javascript(load("static/js/src/openassessment_compose.js"))
        frag.initialize_js('OpenassessmentComposeXBlock')
        return frag

    @XBlock.json_handler
    def submit(self, data, suffix=''):
        """
        Place the submission text into Openassessment system
        """
        # FIXME: Do something
        student_sub = data['submission']
        self.student_sub = student_sub
        return '{"sub": "%s"}' % student_sub

    # TO-DO: change this to create the scenarios you'd like to see in the
    # workbench while developing your XBlock.
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("OpenassessmentComposeXBlock",
             """<vertical_demo>
                <openassessment_compose/>
                </vertical_demo>
             """),
        ]
