"""An XBlock where students can read a question and compose their response"""

import pkg_resources

from mako.template import Template
from openassessment.peer.api import PeerEvaluationWorkflowError

from submissions import api
from openassessment.peer import api as peer_api

from xblock.core import XBlock
from xblock.fields import List, Scope, String
from xblock.fragment import Fragment


mako_default_filters = ['unicode', 'h', 'trim']


class OpenAssessmentBlock(XBlock):
    """Displays a question and gives an area where students can compose a response."""

    start_datetime = String(default=None, scope=Scope.content, help="ISO-8601 formatted string representing the start date of this assignment.")
    due_datetime = String(default=None, scope=Scope.content, help="ISO-8601 formatted string representing the end date of this assignment.")
    prompt = String( default=None, scope=Scope.content, help="A prompt to display to a student (plain text).")
    rubric = List( default=None, scope=Scope.content, help="Instructions and criteria for students giving feedback.")
    rubric_instructions = String( default=None, scope=Scope.content, help="Instructions for self and peer assessment.")
    rubric_criteria = List(default=None, scope=Scope.content, help="The different parts of grading for students giving feedback.")
    rubric_evals = List(default=None, scope=Scope.content, help="The requested set of evaluations and the order in which to apply them.")
    course_id = String( default=u"TestCourse", scope=Scope.content, help="The course_id associated with this prompt (until we can get it from runtime).",)

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
        interactions emenating from this interaction.

        Useful for logging, debugging, and uniqueification."""
        return (self.scope_ids.usage_id, self.scope_ids.user_id)

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
        """The main view of OpenAssessmentBlock, displayed when viewing courses."""
        def load(path):
            """Handy helper for getting resources from our kit."""
            data = pkg_resources.resource_string(__name__, path)
            return data.decode("utf8")

        trace = self._get_xblock_trace()
        student_item_dict = self._get_student_item_dict()
        previous_submissions = api.get_submissions(student_item_dict)
        try:
            peer_submission = peer_api.get_submission_to_evaluate(student_item_dict)
        except PeerEvaluationWorkflowError:
            peer_submission = False

        if previous_submissions and peer_submission:  # XXX: until workflow better, move on w/ prev submit
            html = Template(load("static/html/oa_rubric.html"),
                            default_filters=mako_default_filters,
                            input_encoding='utf-8',
                           )
            frag = Fragment(html.render_unicode(xblock_trace=trace,
                                                peer_submission=peer_submission,
                                                rubric_instructions=self.rubric_instructions,
                                                rubric_criteria=self.rubric_criteria,
                                               ))
            frag.add_css(load("static/css/openassessment.css"))
            frag.add_javascript(load("static/js/src/oa_assessment.js"))
            frag.initialize_js('OpenAssessmentBlock')
        elif previous_submissions:
            # TODO: TIM-39 They're done grading or there is nothing to grade yet.
            pass
        else:                     # XXX: until workflow better, submit until submitted
            html = Template(load("static/html/oa_submission.html"),
                            default_filters=mako_default_filters,
                            input_encoding='utf-8',
                           )
            frag = Fragment(html.render_unicode(xblock_trace=trace, question=self.prompt))
            frag.add_css(load("static/css/openassessment.css"))
            frag.add_javascript(load("static/js/src/oa_submission.js"))
            frag.initialize_js('OpenAssessmentBlock')
        return frag

    @XBlock.json_handler
    def assess(self, data, suffix=''):
        """Place an assessment into Openassessment system"""
        # TODO: We're not doing points possible, right way to do points possible
        # is to refactor the rubric criteria type, Joe has thoughts on this.
        student_item_dict = self._get_student_item_dict()
        assessment_dict = {
            "points_earned": map(int, data["points_earned"]),
            "points_possible": 12,
            "feedback": "Not yet implemented.",
        }
        evaluation = peer_api.create_evaluation(
            data["submission_uuid"],
            student_item_dict["student_id"],
            assessment_dict
        )
        return evaluation, "Success"

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
        return (status, status_tag, status_text)

    @classmethod
    def parse_xml(cls, node, runtime, keys, id_generator):
        """Instantiate xblock object from runtime XML definition."""
        block = runtime.construct_xblock_from_class(cls, keys)
        for child in node:
            if child.tag == 'prompt':
                block.prompt = child.text.strip()
            elif child.tag == 'rubric':
                block.rubric_instructions = child.text.strip()
                block.rubric_criteria = []
                for criterion in child:
                    crit = {'name': criterion.attrib.get('name', ''),
                            'instructions': criterion.text.strip(),
                           }
                    for option in criterion:
                        crit[option.attrib['val']] = option.text.strip()
                    block.rubric_criteria.append(crit)
            elif child.tag == 'evals':
                block.rubric_evals = []
                for evaluation in child:
                    e = {'type': evaluation.tag,
                         'name': evaluation.attrib.get('name', ''),
                         'start_datetime': evaluation.attrib.get('start', None),
                         'due_datetime': evaluation.attrib.get('due', None),
                         # These attrs are accepted for self, ai evals, but ignored:
                         'must_grade': evaluation.attrib.get('must_grade', 1),
                         'must_be_graded_by': evaluation.attrib.get('must_be_graded_by', 0), }
                    block.rubric_evals.append(e)
            else:
                # XXX: jrbl thinks this lets you embed other blocks inside this (?)
                block.runtime.add_node_as_child(block, child, id_generator)
        return block

    # Arbitrary attributes can be defined on the 
    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("OpenAssessmentBlock Poverty Rubric", 
             """
<vertical_demo>

<openassessment start="2014-12-19T23:00-7:00" due="2014-12-21T23:00-7:00">
  <prompt>
    Given the state of the world today, what do you think should be done to
    combat poverty? Please answer in a short essay of 200-300 words.
  </prompt>
  <rubric>
    Read for conciseness, clarity of thought, and form.
    <criterion name="concise">
      How concise is it?
      <option val="0">Neal Stephenson (late)</option>
      <option val="1">HP Lovecraft</option>
      <option val="3">Robert Heinlein</option>
      <option val="4">Neal Stephenson (early)</option>
      <option val="5">Earnest Hemingway</option>
    </criterion>
    <criterion name="clearheaded">
      How clear is the thinking?
      <option val="0">The Unabomber</option>
      <option val="1">Hunter S. Thompson</option>
      <option val="2">Robert Heinlein</option>
      <option val="3">Isaac Asimov</option>
      <option val="55">Spock</option>
    </criterion>
    <criterion name="form">
      Lastly, how is it's form? Punctuation, grammar, and spelling all count.
      <option val="0">lolcats</option>
      <option val="1">Facebook</option>
      <option val="2">Reddit</option>
      <option val="3">metafilter</option>
      <option val="4">Usenet, 1996</option>
      <option val="99">The Elements of Style</option>
    </criterion>
  </rubric>
  <evals>
    <peereval start="2014-12-20T19:00-7:00"
              due="2014-12-21T22:22-7:00"
              must_grade="5"
              must_be_graded_by="3" />
    <selfeval/>
  </evals>
</openassessment>

</vertical_demo>
             """),
            ("OpenAssessmentBlock Censorship Rubric", 
             """
<vertical_demo>

<openassessment start="2013-12-19T23:00-7:00" due="2014-12-21T23:00-7:00">
  <prompt>
    What do you think about censorship in libraries? I think it's pretty great.
  </prompt>
  <rubric>
    Read for conciseness, clarity of thought, and form.
    <criterion name="concise">
      How concise is it?
      <option val="0">The Bible</option>
      <option val="1">Earnest Hemingway</option>
      <option val="3">Matsuo Basho</option>
    </criterion>
    <criterion name="clearheaded">
      How clear is the thinking?
      <option val="0">Eric</option>
      <option val="1">John</option>
      <option val="2">Ian</option>
    </criterion>
    <criterion name="form">
      Lastly, how is it's form? Punctuation, grammar, and spelling all count.
      <option val="0">IRC</option>
      <option val="1">Real Email</option>
      <option val="2">Old-timey letters</option>
    </criterion>
  </rubric>
  <evals>
    <selfeval/>
    <peereval start="2014-12-20T19:00-7:00"
              due="2014-12-21T22:22-7:00"
              must_grade="5"
              must_be_graded_by="3" />
  </evals>
</openassessment>

</vertical_demo>
             """),
        ]

