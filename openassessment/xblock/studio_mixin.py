"""
Studio editing view for OpenAssessment XBlock.
"""
import pkg_resources
import copy
import logging
from django.template.context import Context
from django.template.loader import get_template
from django.utils.translation import ugettext as _, ugettext
from xblock.core import XBlock
from xblock.fragment import Fragment
from openassessment.xblock import xml
from openassessment.xblock.validation import validator
from openassessment.xblock.xml import UpdateFromXmlError, parse_date, parse_examples_xml_str


logger = logging.getLogger(__name__)


class StudioMixin(object):
    """
    Studio editing view for OpenAssessment XBlock.
    """

    def studio_view(self, context=None):
        """
        Render the OpenAssessment XBlock for editing in Studio.

        Args:
            context: Not actively used for this view.

        Returns:
            (Fragment): An HTML fragment for editing the configuration of this XBlock.
        """
        rendered_template = get_template('openassessmentblock/oa_edit.html').render(Context({}))
        frag = Fragment(rendered_template)
        frag.add_javascript(pkg_resources.resource_string(__name__, "static/js/openassessment.min.js"))
        frag.initialize_js('OpenAssessmentEditor')
        return frag

    @XBlock.json_handler
    def update_editor_context(self, data, suffix=''):
        """
        Update the XBlock's configuration.

        Args:
            data (dict): Data from the request; should have a value for the keys: 'rubric', 'prompt',
            'title', 'submission_start', 'submission_due', and 'assessments'.
                -- The 'rubric' should be an XML representation of the new rubric.
                -- The 'prompt' and 'title' should be plain text.
                -- The dates 'submission_start' and 'submission_due' are both ISO strings
                -- The 'assessments' is a list of assessment dictionaries (much like self.rubric_assessments)
                   with the notable exception that all examples (for Student Training and eventually AI)
                   are in XML string format and need to be parsed into dictionaries.

        Kwargs:
            suffix (str): Not used

        Returns:
            dict with keys 'success' (bool) and 'msg' (str)
        """
        missing_keys = list(
            {'rubric', 'prompt', 'title', 'assessments', 'submission_start', 'submission_due'} - set(data.keys())
        )
        if missing_keys:
            logger.warn(
                'Must specify the following missing keys in request JSON dict: {}'.format(missing_keys)
            )
            return {'success': False, 'msg': _('Error updating XBlock configuration')}

        try:
            rubric = verify_rubric_format(data['rubric'])
            submission_due = xml.parse_date(data["submission_due"], name="submission due date")
            submission_start = xml.parse_date(data["submission_start"], name="submission start date")
            assessments = parse_assessment_dictionaries(data["assessments"])
        except xml.UpdateFromXmlError as ex:
            return {'success': False, 'msg': _('An error occurred while saving: {error}').format(error=ex)}

        xblock_validator = validator(self)
        success, msg = xblock_validator(rubric, {'due': submission_due, 'start': submission_start}, assessments)
        if not success:
            return {'success': False, 'msg': _('Validation error: {error}').format(error=msg)}

        self.update(
            rubric.get('criteria', []),
            rubric.get('feedbackprompt', None),
            assessments,
            submission_due,
            submission_start,
            data["title"],
            data["prompt"]
        )
        return {'success': True, 'msg': 'Successfully updated OpenAssessment XBlock'}

    @XBlock.json_handler
    def editor_context(self, data, suffix=''):
        """
        Retrieve the XBlock's content definition, serialized as a JSON object
        containing all the configuration as it will be displayed for studio
        editing.

        Args:
            data (dict): Not used

        Kwargs:
            suffix (str): Not used

        Returns:
            dict with keys
                'success' (bool),  'message' (unicode),  'rubric' (unicode),  'prompt' (unicode),
                'title' (unicode),  'submission_start' (unicode),  'submission_due' (unicode),  'assessments (dict)

        """
        try:
            # Copies the rubric assessments so that we can change student training examples from dict -> str without
            # negatively modifying the openassessmentblock definition.
            assessment_list = copy.deepcopy(self.rubric_assessments)
            # Finds the student training dictionary, if it exists, and replaces the examples with their XML definition
            student_training_dictionary = [d for d in assessment_list if d["name"] == "student-training"]
            if student_training_dictionary:
                # Our for loop will return a list.  Select the first element of that list if it exists.
                student_training_dictionary = student_training_dictionary[0]
                examples = xml.serialize_examples_to_xml_str(student_training_dictionary)
                student_training_dictionary["examples"] = examples

        # We do not expect serialization to raise an exception, but if it does, handle it gracefully.
        except:
            logger.exception("An error occurred while serializing the XBlock")
            msg = _('An unexpected error occurred while loading the problem')
            return {'success': False, 'msg': msg, 'xml': u''}

        # Populates the context for the assessments section of the editing
        # panel. This will adjust according to the fields laid out in this
        # section.

        submission_due = self.submission_due if self.submission_due else ''
        submission_start = self.submission_start if self.submission_start else ''

        rubric_dict = {
            'criteria' : self.rubric_criteria,
            'feedbackprompt': unicode(self.rubric_feedback_prompt)
        }

        return {
            'success': True,
            'msg': '',
            'rubric': rubric_dict,
            'prompt': self.prompt,
            'submission_due': submission_due,
            'submission_start': submission_start,
            'title': self.title,
            'assessments': assessment_list
        }

    @XBlock.json_handler
    def check_released(self, data, suffix=''):
        """
        Check whether the problem has been released.

        Args:
            data (dict): Not used

        Kwargs:
            suffix (str): Not used

        Returns:
            dict with keys 'success' (bool), 'message' (unicode), and 'is_released' (bool)
        """
        # There aren't currently any server-side error conditions we report to the client,
        # but we send success/msg values anyway for consistency with other handlers.
        return {
            'success': True, 'msg': u'',
            'is_released': self.is_released()
        }


def parse_assessment_dictionaries(input_assessments):
    """
    Parses the elements of assessment dictionaries returned by the Studio UI into storable rubric_assessments

    Args:
        input_assessments (list of dict): A list of the dictionaries that are assembled in Javascript to
                represent their modules.  Some changes need to be made between this and the result:
                        -- Parse the XML examples from the Student Training and or AI
                        -- Parse all dates (including the assessment dates) correctly

    Returns:
        (list of dict): Can be directly assigned/stored in an openassessmentblock.rubric_assessments
    """

    assessments_list = []

    for assessment in input_assessments:

        assessment_dict = dict()

        # Assessment name
        if 'name' in assessment:
            assessment_dict['name'] = assessment.get('name')
        else:
            raise UpdateFromXmlError(_('All "assessment" elements must contain a "name" element.'))

        # Assessment start
        if 'start' in assessment:
            parsed_start = parse_date(assessment.get('start'), name="{} start date".format(assessment.get('name')))
            assessment_dict['start'] = parsed_start
        else:
            assessment_dict['start'] = None

        # Assessment due
        if 'due' in assessment:
            parsed_due = parse_date(assessment.get('due'), name="{} due date".format(assessment.get('name')))
            assessment_dict['due'] = parsed_due

        else:
            assessment_dict['due'] = None

        # Assessment must_grade
        if 'must_grade' in assessment:
            try:
                assessment_dict['must_grade'] = int(assessment.get('must_grade'))
            except (ValueError, TypeError):
                raise UpdateFromXmlError(_('The "must_grade" value must be a positive integer.'))

        # Assessment must_be_graded_by
        if 'must_be_graded_by' in assessment:
            try:
                assessment_dict['must_be_graded_by'] = int(assessment.get('must_be_graded_by'))
            except (ValueError, TypeError):
                raise UpdateFromXmlError(_('The "must_be_graded_by" value must be a positive integer.'))

        # Training examples (can be for AI OR for Student Training)
        if 'examples' in assessment:
            try:
                assessment_dict['examples'] = parse_examples_xml_str(assessment.get('examples'))
            except UpdateFromXmlError as ex:
                raise UpdateFromXmlError(_("There was an error in parsing the {name} examples: {ex}").format(
                    name=assessment_dict['name'], ex=ex
                ))

        # Update the list of assessments
        assessments_list.append(assessment_dict)

    return assessments_list


def verify_rubric_format(rubric):
    """
    Verifies that the rubric that was passed in follows the conventions that we expect, including
    types and structure.

    Args:
        rubric (dict): Unsanitized version of our rubric.  Usually taken from the GUI.

    Returns:
        rubric (dict): Sanitized version of the same form.

    Raises:
        UpdateFromXMLError
    """

    if not isinstance(rubric, dict):
        raise UpdateFromXmlError(_("The given rubric was not a dictionary of the form {criteria: [criteria1, criteria2...]}"))

    if "criteria" not in rubric.keys():
        raise UpdateFromXmlError(_("The given rubric did not contain a key for a list of criteria, and is invalid"))

    if rubric.get('prompt', False):
        if not isinstance(rubric['prompt'], basestring):
            raise UpdateFromXmlError(_("The given rubric's feedback prompt was invalid, it must be a string."))

    criteria = rubric["criteria"]

    if not isinstance(criteria, list):
        raise UpdateFromXmlError(_("The criteria term in the rubric dictionary corresponds to a non-list object."))

    sanitized_criteria = []

    for criterion in criteria:
        if not isinstance(criterion, dict):
            raise UpdateFromXmlError(_("A criterion given was not a dictionary."))

        criterion = dict(criterion)

        expected_keys = {'order_num', 'name', 'prompt', 'options', 'feedback'}
        missing_keys = expected_keys - set(criterion.keys())

        if missing_keys:
            raise UpdateFromXmlError(_("The following keys were missing from the definition of one or more criteria: {}".format(", ".join(missing_keys))))

        try:
            name = unicode(criterion['name'])
        except (TypeError, ValueError):
            raise UpdateFromXmlError(_("The name value must be a string."))

        try:
            prompt = unicode(criterion['prompt'])
        except (TypeError, ValueError):
            raise UpdateFromXmlError(_("The prompt value must be a string."))

        try:
            feedback = unicode(criterion['feedback'])
        except (TypeError, ValueError):
            raise UpdateFromXmlError(_("The prompt value must be a string."))

        try:
            order_num = int(criterion['order_num'])
        except (TypeError, ValueError):
            raise UpdateFromXmlError(_("The order_num value must be an integer."))

        if not isinstance(criterion['options'], list):
            raise UpdateFromXmlError(_("The dictionary entry for 'options' in a criteria's dictionary definition must be a list."))

        options = criterion['options']

        sanitized_options = []

        for option in options:

            if not isinstance(option, dict):
                raise UpdateFromXmlError(_("An option given was not a dictionary."))

            expected_keys = {'order_num', 'name', 'points', 'explanation'}
            unexpected_keys = list(set(option.keys()) - expected_keys)
            missing_keys = list(expected_keys - set(option.keys()))

            if missing_keys:
                raise UpdateFromXmlError(_("The following keys were missing from the definition of one or more options: {}".format(", ".join(missing_keys))))

            try:
                option_name = unicode(option['name'])
            except (TypeError, ValueError):
                raise UpdateFromXmlError(_("All option names values must be strings."))

            try:
                option_explanation = unicode(option['explanation'])
            except (TypeError, ValueError):
                raise UpdateFromXmlError(_("All option explanation values must be strings."))

            try:
                option_points = int(option['points'])
            except (TypeError, ValueError):
                raise UpdateFromXmlError(_("All option point values must be integers."))

            option_dict = {
                "order_num": option['order_num'],
                "name": option_name,
                "explanation": option_explanation,
                "points": option_points
            }

            sanitized_options.append(option_dict)

        criterion_dict = {
            "order_num": order_num,
            "name": name,
            "prompt": prompt,
            "options": sanitized_options,
            "feedback": feedback
        }

        sanitized_criteria.append(criterion_dict)

    sanitized_rubric = {
        'criteria': sanitized_criteria
    }

    if rubric.get('prompt'):
        try:
            sanitized_rubric['prompt'] = unicode(rubric.get('prompt'))
        except (TypeError, ValueError):
            raise UpdateFromXmlError(_("All prompt values must be strings."))

    return sanitized_rubric
