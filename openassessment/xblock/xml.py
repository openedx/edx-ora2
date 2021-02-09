"""
Serialize and deserialize OpenAssessment XBlock content to/from XML.
"""


import json
import logging
from uuid import uuid4 as uuid

import dateutil.parser
import defusedxml.ElementTree as safe_etree
import pytz

import lxml.etree as etree
from openassessment.xblock.data_conversion import update_assessments_format
from openassessment.xblock.lms_mixin import GroupAccessDict

log = logging.getLogger(__name__)


class UpdateFromXmlError(Exception):
    """
    Error occurred while deserializing the OpenAssessment XBlock content from XML.
    """


class ValidationError(UpdateFromXmlError):
    """
    The XML definition is not semantically valid.
    """


def _sort_by_order_num(items):
    """
    Sort dictionaries by the key "order_num".
    If no order number is specified, assign an arbitrary order.
    Ignores non-dict items in the list.

    Args:
        items (list): List of dictionaries to sort.

    Returns:
        dict
    """
    return sorted(
        [el for el in items if isinstance(el, dict)],
        key=lambda el: el.get('order_num', 0)
    )


def _safe_get_text(element):
    """
    Retrieve the text from the element, safely handling empty elements.

    Args:
        element (lxml.etree.Element): The XML element.

    Returns:
        unicode
    """
    return str(element.text) if element.text is not None else ""


def _serialize_prompts(prompts_root, prompts_list):
    """
    Serialize prompts as XML, adding children to the XML with root
    node `prompts_root`.

    Args:
        prompts_root (lxml.etree.Element): The root node of the tree.
        prompts_list (list): List of prompt dictionaries.

    Returns:
        None
    """
    if not isinstance(prompts_list, list):
        return

    for prompt in prompts_list:
        prompt_el = etree.SubElement(prompts_root, 'prompt')

        # Prompt description
        prompt_description = etree.SubElement(prompt_el, 'description')
        prompt_description.text = str(prompt.get('description', ''))


def _serialize_options(options_root, options_list):
    """
    Serialize rubric criterion options as XML, adding children to the XML
    with root node `options_root`.

    We don't make any assumptions about the contents of `options_list`,
    and we handle unexpected inputs gracefully.

    Args:
        options_root (lxml.etree.Element): The root node of the tree.
        options_list (list): List of options dictionaries.

    Returns:
        None
    """
    # Sort the options by order number, then serialize as XML
    for option in _sort_by_order_num(options_list):
        option_el = etree.SubElement(options_root, 'option')

        # Points (default to 0)
        option_el.set('points', str(option.get('points', 0)))

        # Name (default to a UUID)
        option_name = etree.SubElement(option_el, 'name')
        if 'name' in option:
            option_name.text = str(option['name'])
        else:
            option_name.text = str(uuid().hex)

        # Label (default to the option name, then an empty string)
        option_label = etree.SubElement(option_el, 'label')
        option_label.text = str(option.get('label', option.get('name', '')))

        # Explanation (default to empty str)
        option_explanation = etree.SubElement(option_el, 'explanation')
        option_explanation.text = str(option.get('explanation', ''))


def _serialize_criteria(criteria_root, criteria_list):
    """
    Serialize rubric criteria as XML, adding children to the XML
    with root node `criteria_root`.

    We don't make any assumptions about the contents of `criteria_list`,
    and we handle unexpected inputs gracefully.

    Args:
        critera_root (lxml.etree.Element): The root node of the tree.
        criteria_list (list): List of criteria dictionaries.

    Returns:
        None
    """

    # Sort the criteria by order number, then serialize as XML
    for criterion in _sort_by_order_num(criteria_list):
        criterion_el = etree.SubElement(criteria_root, 'criterion')

        # Criterion name (default to a UUID)
        criterion_name = etree.SubElement(criterion_el, 'name')
        if 'name' in criterion:
            criterion_name.text = str(criterion['name'])
        else:
            criterion_name.text = str(uuid().hex)

        # Criterion label (default to the name, then an empty string)
        criterion_label = etree.SubElement(criterion_el, 'label')
        criterion_label.text = str(criterion.get('label', criterion.get('name', '')))

        # Criterion prompt (default to empty string)
        criterion_prompt = etree.SubElement(criterion_el, 'prompt')
        criterion_prompt.text = str(criterion.get('prompt', ''))

        # Criterion feedback disabled, optional, or required
        # If disabled, do not set the attribute.
        if criterion.get('feedback') in ["optional", "required"]:
            criterion_el.set('feedback', criterion['feedback'])

        # Criterion options
        options_list = criterion.get('options', None)
        if isinstance(options_list, list):
            _serialize_options(criterion_el, options_list)


def serialize_rubric(rubric_root, oa_block):
    """
    Serialize a rubric dictionary as XML, adding children to the XML
    with root node `rubric_root`.

    This is very liberal in what it accepts.  If the rubric dict persisted
    by the XBlock is invalid for some reason, we still want to generate XML
    so that Studio authors can fix the error.

    Args:
        oa_block (OpenAssessmentBlock): The OpenAssessmentBlock to serialize
        rubric_dict (dict): A dictionary representation of the rubric, of the form
            described in the serialized Rubric model (peer grading serializers).

    Returns:
        None
    """
    # Criteria
    criteria_list = oa_block.rubric_criteria

    if isinstance(criteria_list, list):
        _serialize_criteria(rubric_root, criteria_list)

    if oa_block.rubric_feedback_prompt is not None:
        feedback_prompt = etree.SubElement(rubric_root, 'feedbackprompt')
        feedback_prompt.text = str(oa_block.rubric_feedback_prompt)

    if oa_block.rubric_feedback_default_text is not None:
        feedback_text = etree.SubElement(rubric_root, 'feedback_default_text')
        feedback_text.text = str(oa_block.rubric_feedback_default_text)


def parse_date(date_str, name=""):
    """
    Attempt to parse a date string into ISO format (without milliseconds)
    Returns `None` if this cannot be done.

    Args:
        date_str (str): The date string to parse.

    Kwargs:
        name (str): the name to return in an error to the origin of the call if an error occurs.

    Returns:
        unicode in ISO format (without milliseconds) if the date string is
        parse-able. None if parsing fails.

    Raises:
        UpdateFromXmlError
    """
    if date_str == "":
        return None
    try:
        # Get the date into ISO format
        parsed_date = dateutil.parser.parse(str(date_str)).replace(tzinfo=pytz.utc)
        formatted_date = parsed_date.strftime("%Y-%m-%dT%H:%M:%S")
        return str(formatted_date)
    except (ValueError, TypeError) as ex:
        msg = (
            'The format of the given date ({date}) for the {name} is invalid. '
            'Make sure the date is formatted as YYYY-MM-DDTHH:MM:SS.'
        ).format(date=date_str, name=name)
        raise UpdateFromXmlError(msg) from ex


def _parse_boolean(boolean_str):
    """
    Attempt to parse a boolean string into a boolean value. Leniently accepts
    both 'True' and 'true', but is otherwise declared false.

    Args:
        boolean_str (unicode): The boolean string to parse.

    Returns:
        The boolean value of the string. True if the string equals 'True' or
        'true'
    """
    return boolean_str in ['True', 'true']


def _parse_prompts_xml(root):
    """
    Parse <prompts> element in the OpenAssessment XBlock's content XML.

    Args:
        root (lxml.etree.Element): The root node of the tree.

    Returns:
        list of prompts dictionaries.

    Raises:
        UpdateFromXmlError: The XML definition is invalid or the XBlock could not be updated.
    """
    prompts_list = []

    prompts_el = root.find('prompts')
    if prompts_el is not None:
        for prompt in prompts_el.findall('prompt'):
            prompt_dict = dict()

            # Prompt description
            prompt_description = prompt.find('description')
            if prompt_description is not None:
                prompt_dict['description'] = _safe_get_text(prompt_description)
            else:
                raise UpdateFromXmlError('Every "prompt" element must contain a "description" element.')

            prompts_list.append(prompt_dict)
    else:
        # For backwards compatibility. Initially a single prompt element was added in
        # the rubric element.
        rubric_el = root.find('rubric')
        prompt_el = rubric_el.find('prompt')
        prompt_description = ''
        if prompt_el is not None:
            prompt_description = _safe_get_text(prompt_el)

        prompts_list.append(
            {
                'description': prompt_description,
            }
        )

    return prompts_list


def _parse_options_xml(options_root):
    """
    Parse <options> element in the OpenAssessment XBlock's content XML.

    Args:
        options_root (lxml.etree.Element): The root of the tree.

    Returns:
        list of option dictionaries, as defined in the Rubric model of the peer grading app.

    Raises:
        UpdateFromXmlError: The XML definition is invalid or the XBlock could not be updated.
    """
    options_list = []
    order_num = 0

    for option in options_root.findall('option'):
        option_dict = dict()

        # Option order number (sequential)
        option_dict['order_num'] = order_num
        order_num += 1

        # Option points -- must be an integer!
        if 'points' in option.attrib:
            try:
                option_dict['points'] = int(option.get('points'))
            except ValueError as ex:
                raise UpdateFromXmlError('The value for "points" must be an integer.') from ex
        else:
            raise UpdateFromXmlError('Every "option" element must contain a "points" attribute.')

        # Option name
        option_name = option.find('name')
        if option_name is not None:
            option_dict['name'] = _safe_get_text(option_name)
        else:
            raise UpdateFromXmlError('Every "option" element must contain a "name" element.')

        # Option label
        # Backwards compatibility: Older problem definitions won't have this.
        # If no label is defined, default to the option name.
        option_label = option.find('label')
        option_dict['label'] = (
            _safe_get_text(option_label)
            if option_label is not None
            else option_dict['name']
        )

        # Option explanation
        option_explanation = option.find('explanation')
        if option_explanation is not None:
            option_dict['explanation'] = _safe_get_text(option_explanation)
        else:
            raise UpdateFromXmlError('Every "option" element must contain an "explanation" element.')

        # Add the options dictionary to the list
        options_list.append(option_dict)

    return options_list


def _parse_criteria_xml(criteria_root):
    """
    Parse <criteria> element in the OpenAssessment XBlock's content XML.

    Args:
        criteria_root (lxml.etree.Element): The root node of the tree.

    Returns:
        list of criteria dictionaries, as defined in the Rubric model of the peer grading app.

    Raises:
        UpdateFromXmlError: The XML definition is invalid or the XBlock could not be updated.
    """
    criteria_list = []
    order_num = 0

    for criterion in criteria_root.findall('criterion'):
        criterion_dict = dict()

        # Criterion order number (sequential)
        criterion_dict['order_num'] = order_num
        order_num += 1

        # Criterion name
        criterion_name = criterion.find('name')
        if criterion_name is not None:
            criterion_dict['name'] = _safe_get_text(criterion_name)
        else:
            raise UpdateFromXmlError('Every "criterion" element must contain a "name" element.')

        # Criterion label
        # Backwards compatibility: Older problem definitions won't have this,
        # so if it isn't set, default to the criterion name.
        criterion_label = criterion.find('label')
        criterion_dict['label'] = (
            _safe_get_text(criterion_label)
            if criterion_label is not None
            else criterion_dict['name']
        )

        # Criterion prompt
        criterion_prompt = criterion.find('prompt')
        if criterion_prompt is not None:
            criterion_dict['prompt'] = _safe_get_text(criterion_prompt)
        else:
            raise UpdateFromXmlError('Every "criterion" element must contain a "prompt" element.')

        # Criterion feedback (disabled, optional, or required)
        criterion_feedback = criterion.get('feedback', 'disabled')
        if criterion_feedback in ['optional', 'disabled', 'required']:
            criterion_dict['feedback'] = criterion_feedback
        else:
            raise UpdateFromXmlError(
                'Invalid value for "feedback" attribute: if specified, it must be set set to "optional" or "required".'
            )

        # Criterion options
        criterion_dict['options'] = _parse_options_xml(criterion)

        # Add the newly constructed criterion dict to the list
        criteria_list.append(criterion_dict)

    return criteria_list


def parse_rubric_xml(rubric_root):
    """
    Parse <rubric> element in the OpenAssessment XBlock's content XML.

    Args:
        rubric_root (lxml.etree.Element): The root of the <rubric> node in the tree.

    Returns:
        dict, a serialized representation of a rubric, as defined by the peer grading serializers.

    Raises:
        UpdateFromXmlError: The XML definition is invalid or the XBlock could not be updated.
        InvalidRubricError: The rubric was not semantically valid.
    """
    rubric_dict = dict()

    feedback_prompt_el = rubric_root.find('feedbackprompt')
    if feedback_prompt_el is not None:
        rubric_dict['feedbackprompt'] = _safe_get_text(feedback_prompt_el)
    else:
        rubric_dict['feedbackprompt'] = None

    feedback_text_el = rubric_root.find('feedback_default_text')
    if feedback_text_el is not None:
        rubric_dict['feedback_default_text'] = _safe_get_text(feedback_text_el)
    else:
        rubric_dict['feedback_default_text'] = None

    # Criteria
    rubric_dict['criteria'] = _parse_criteria_xml(rubric_root)

    return rubric_dict


def parse_examples_xml(examples):
    """
    Parse <example> (training examples) from the XML.

    Args:
        examples (list of lxml.etree.Element): The <example> elements to parse.

    Returns:
        list of example dicts

    Raises:
        UpdateFromXmlError

    """
    examples_list = []
    for example_el in examples:
        example_dict = dict()

        # Retrieve the answers from the training example
        answers_list = list()
        answer_elements = example_el.findall('answer')
        if len(answer_elements) != 1:
            raise UpdateFromXmlError('Each "example" element must contain exactly one "answer" element')

        answer_part_elements = answer_elements[0].findall('part')
        if answer_part_elements:
            for answer_part_element in answer_part_elements:
                answers_list.append(_safe_get_text(answer_part_element))
        else:
            # Initially example answers had only one part.
            answers_list.append(_safe_get_text(answer_elements[0]))

        example_dict['answer'] = {"parts": [{"text": text} for text in answers_list]}

        # Retrieve the options selected from the training example
        example_dict['options_selected'] = []
        for select_el in example_el.findall('select'):
            if 'criterion' not in select_el.attrib:
                raise UpdateFromXmlError('Each "select" element must have a "criterion" attribute')
            if 'option' not in select_el.attrib:
                raise UpdateFromXmlError('Each "select" element must have an "option" attribute')

            example_dict['options_selected'].append({
                'criterion': str(select_el.get('criterion')),
                'option': str(select_el.get('option'))
            })

        examples_list.append(example_dict)

    return examples_list


def parse_assessments_xml(assessments_root):
    """
    Parse the <assessments> element in the OpenAssessment XBlock's content XML.

    Args:
        assessments_root (lxml.etree.Element): The root of the <assessments> node in the tree.

    Returns:
        list of assessment dicts

    Raises:
        UpdateFromXmlError

    """
    assessments_list = []

    for assessment in assessments_root.findall('assessment'):

        assessment_dict = dict()

        # Assessment name
        if 'name' in assessment.attrib:
            assessment_dict['name'] = str(assessment.get('name'))
        else:
            raise UpdateFromXmlError('All "assessment" elements must contain a "name" element.')

        # Assessment start
        if 'start' in assessment.attrib:

            # Other assessment types CAN have a start date
            # pylint: disable=unicode-format-string
            parsed_start = parse_date(assessment.get('start'), name="{} start date".format(assessment_dict['name']))

            if parsed_start is not None:
                assessment_dict['start'] = parsed_start
        else:
            assessment_dict['start'] = None

        # Assessment due
        if 'due' in assessment.attrib:

            # Other assessment types CAN have a due date
            # pylint: disable=unicode-format-string
            parsed_due = parse_date(assessment.get('due'), name="{} due date".format(assessment_dict['name']))

            if parsed_due is not None:
                assessment_dict['due'] = parsed_due
        else:
            assessment_dict['due'] = None

        # Assessment must_grade
        if 'must_grade' in assessment.attrib:
            try:
                assessment_dict['must_grade'] = int(assessment.get('must_grade'))
            except ValueError as ex:
                raise UpdateFromXmlError('The "must_grade" value must be a positive integer.') from ex

        # Assessment must_be_graded_by
        if 'must_be_graded_by' in assessment.attrib:
            try:
                assessment_dict['must_be_graded_by'] = int(assessment.get('must_be_graded_by'))
            except ValueError as ex:
                raise UpdateFromXmlError('The "must_be_graded_by" value must be a positive integer.') from ex

        # Assessment enable_flexible_grading
        if 'enable_flexible_grading' in assessment.attrib:
            try:
                assessment_dict['enable_flexible_grading'] = _parse_boolean(assessment.get('enable_flexible_grading'))
            except ValueError as ex:
                raise UpdateFromXmlError('The "enable_flexible_grading" value must be a boolean.') from ex

        # Assessment required
        if 'required' in assessment.attrib:

            # Staff assessment is the only type to use an explicit required marker
            if assessment_dict['name'] != 'staff-assessment':
                raise UpdateFromXmlError('The "required" field is only allowed for staff assessment.')
            assessment_dict['required'] = _parse_boolean(str(assessment.get('required')))

        # Training examples
        examples = assessment.findall('example')

        # Student training and AI Grading should always have examples set, even if it's an empty list.
        # (Validation rules, applied later, are responsible for
        # ensuring that users specify at least one example).
        # All assessments except for Student Training ignore examples.
        if assessment_dict['name'] == 'student-training':
            assessment_dict['examples'] = parse_examples_xml(examples)

        # Update the list of assessments
        assessments_list.append(assessment_dict)

    return assessments_list


def serialize_training_examples(examples, assessment_el):
    """
    Serialize a training example to XML.

    Args:
        examples (list of dict): List of example dictionaries.
        assessment_el (lxml.etree.Element): The <assessment> XML element.

    Returns:
        None

    """
    for example_dict in examples:
        example_el = etree.SubElement(assessment_el, 'example')

        # Answer provided in the example (default to empty string)
        answer_el = etree.SubElement(example_el, 'answer')
        try:
            answer = example_dict.get('answer')
            if answer is None:
                parts = []
            elif isinstance(answer, dict):
                parts = answer.get('parts', [])
            elif isinstance(answer, list):
                parts = answer

            for part in parts:
                part_el = etree.SubElement(answer_el, 'part')
                # pylint: disable=unicode-format-string
                part_el.text = str(part.get('text', ''))
        except Exception:  # excuse the bare-except, looking for more information on EDUCATOR-1817
            log.exception('Error parsing training example: %s', example_dict)
            raise

        # Options selected from the rubric
        options_selected = example_dict.get('options_selected', [])
        for selected_dict in options_selected:
            select_el = etree.SubElement(example_el, 'select')
            select_el.set('criterion', str(selected_dict.get('criterion', '')))
            select_el.set('option', str(selected_dict.get('option', '')))


def serialize_assessments(assessments_root, oa_block):
    """
    Serialize the assessment modules for an OpenAssessment XBlock.

    Args:
        assessments_root (lxml.etree.Element): The <assessments> XML element.
        oa_block (OpenAssessmentXBlock): The XBlock with configuration to
            serialize.

    Returns:
        None

    """
    for assessment_dict in update_assessments_format(oa_block.rubric_assessments):

        assessment = etree.SubElement(assessments_root, 'assessment')

        # Set assessment attributes, defaulting to empty values
        assessment.set('name', str(assessment_dict.get('name', '')))

        if 'must_grade' in assessment_dict:
            assessment.set('must_grade', str(assessment_dict['must_grade']))

        if 'must_be_graded_by' in assessment_dict:
            assessment.set('must_be_graded_by', str(assessment_dict['must_be_graded_by']))

        if 'enable_flexible_grading' in assessment_dict:
            assessment.set('enable_flexible_grading', str(assessment_dict['enable_flexible_grading']))

        if assessment_dict.get('start') is not None:
            assessment.set('start', str(assessment_dict['start']))

        if assessment_dict.get('due') is not None:
            assessment.set('due', str(assessment_dict['due']))

        if assessment_dict.get('required') is not None:
            assessment.set('required', str(assessment_dict['required']))

        # Training examples
        examples = assessment_dict.get('examples', [])
        if not isinstance(examples, list):
            examples = []
        serialize_training_examples(examples, assessment)


def serialize_content_to_xml(oa_block, root):
    """
    Serialize the OpenAssessment XBlock's content to XML.

    Args:
        oa_block (OpenAssessmentBlock): The open assessment block to serialize.
        root (etree.Element): The XML root node to update.

    Returns:
        etree.Element

    """
    root.tag = 'openassessment'

    # Set the submission start date
    if oa_block.submission_start is not None:
        root.set('submission_start', str(oa_block.submission_start))

    # Set submission due date
    if oa_block.submission_due is not None:
        root.set('submission_due', str(oa_block.submission_due))

    # Set leaderboard show
    if oa_block.leaderboard_show:
        root.set('leaderboard_show', str(oa_block.leaderboard_show))

    # Set text response
    if oa_block.text_response:
        root.set('text_response', str(oa_block.text_response))

    # Set text response editor
    if oa_block.text_response_editor:
        root.set('text_response_editor', str(oa_block.text_response_editor))

    # Set file upload response
    if oa_block.file_upload_response:
        root.set('file_upload_response', str(oa_block.file_upload_response))

    # Set File upload settings
    if oa_block.file_upload_type:
        root.set('file_upload_type', str(oa_block.file_upload_type))

    # Set File type white listing
    if oa_block.white_listed_file_types:
        root.set('white_listed_file_types', str(oa_block.white_listed_file_types_string))

    if oa_block.allow_multiple_files is not None:
        root.set('allow_multiple_files', str(oa_block.allow_multiple_files))

    if oa_block.allow_latex is not None:
        root.set('allow_latex', str(oa_block.allow_latex))

    # Set group access setting if not empty
    if oa_block.group_access:
        root.set('group_access', json.dumps(GroupAccessDict().to_json(oa_block.group_access)))

    # Open assessment displayed title
    title = etree.SubElement(root, 'title')
    title.text = str(oa_block.title)

    # Assessment list
    assessments_root = etree.SubElement(root, 'assessments')
    serialize_assessments(assessments_root, oa_block)

    # Prompts
    prompts_root = etree.SubElement(root, 'prompts')
    _serialize_prompts(prompts_root, oa_block.prompts)

    root.set('prompts_type', str(oa_block.prompts_type))

    # Rubric
    rubric_root = etree.SubElement(root, 'rubric')
    serialize_rubric(rubric_root, oa_block)

    # Team info
    if oa_block.teams_enabled is not None:
        root.set('teams_enabled', str(oa_block.teams_enabled))
    if oa_block.selected_teamset_id is not None:
        root.set('selected_teamset_id', str(oa_block.selected_teamset_id))

    if oa_block.show_rubric_during_response is not None:
        root.set('show_rubric_during_response', str(oa_block.show_rubric_during_response))


def serialize_content(oa_block):
    """
    Serialize the OpenAssessment XBlock's content to an XML string.

    Args:
        oa_block (OpenAssessmentBlock): The open assessment block to serialize.

    Returns:
        xml (unicode)
    """
    root = etree.Element('openassessment')
    serialize_content_to_xml(oa_block, root)

    # Return a UTF-8 representation of the XML
    return etree.tostring(root, pretty_print=True, encoding='unicode')


def serialize_rubric_to_xml_str(oa_block):
    """
    Serialize the OpenAssessment XBlock's rubric into an XML string. This is
    designed to serialize the XBlock's rubric specifically for authoring. Since
    the authoring view splits the prompt from the rubric, the serialized format
    for the rubric does not contain the prompt.

    Args:
        oa_block (OpenAssessmentBlock): The open assessment block to serialize
            a rubric from.

    Returns:
        xml (unicode) representation of the Rubric.

    """
    rubric_root = etree.Element('rubric')
    serialize_rubric(rubric_root, oa_block)
    return etree.tostring(rubric_root, pretty_print=True, encoding='unicode')


def serialize_examples_to_xml_str(assessment):
    """
    Serializes the OpenAssessment XBlock's training examples into an XML unicode
    string.

    Args:
        assessment (dict): Dictionary representation of an Assessment Module's
            configuration. If this contains a list of examples, the examples
            will be returned serialized.

    Returns:
        A unicode string of the XML serialized examples.

    """
    examples = update_assessments_format([assessment])[0].get('examples', [])
    if not isinstance(examples, list):
        examples = []
    examples_root = etree.Element('examples')
    serialize_training_examples(examples, examples_root)
    return etree.tostring(examples_root, pretty_print=True, encoding='unicode')


def serialize_assessments_to_xml_str(oa_block):
    """
    Serializes the OpenAssessment XBlock's assessment modules into an XML
    unicode string.

    Args:
        oa_block (OpenAssessmentBlock
    """
    assessments_root = etree.Element('assessments')
    serialize_assessments(assessments_root, oa_block)
    return etree.tostring(assessments_root, pretty_print=True, encoding='unicode')


def parse_from_xml(root):
    """
    Update the OpenAssessment XBlock's content from an XML definition.

    We need to be strict about the XML we accept, to avoid setting
    the XBlock to an invalid state (which will then be persisted).

    Args:
        root (lxml.etree.Element): The XML definition of the XBlock's content.

    Returns:
        A dictionary of all of the XBlock's content.

    Raises:
        UpdateFromXmlError: The XML definition is invalid
    """

    # Check that the root has the correct tag
    if root.tag != 'openassessment':
        raise UpdateFromXmlError('Every open assessment problem must contain an "openassessment" element.')

    # Retrieve the start date for the submission
    # Set it to None by default; we will update it to the latest start date later on
    submission_start = None
    if 'submission_start' in root.attrib:
        submission_start = parse_date(str(root.attrib['submission_start']), name="submission start date")

    # Retrieve the due date for the submission
    # Set it to None by default; we will update it to the earliest deadline later on
    submission_due = None
    if 'submission_due' in root.attrib:
        submission_due = parse_date(str(root.attrib['submission_due']), name="submission due date")

    text_response = None
    if 'text_response' in root.attrib:
        text_response = str(root.attrib['text_response'])

    text_response_editor = 'text'
    if 'text_response_editor' in root.attrib:
        text_response_editor = str(root.attrib['text_response_editor'])

    file_upload_response = None
    if 'file_upload_response' in root.attrib:
        file_upload_response = str(root.attrib['file_upload_response'])

    allow_file_upload = None
    if 'allow_file_upload' in root.attrib:
        allow_file_upload = _parse_boolean(str(root.attrib['allow_file_upload']))

    file_upload_type = None
    if 'file_upload_type' in root.attrib:
        file_upload_type = str(root.attrib['file_upload_type'])

    white_listed_file_types = None
    if 'white_listed_file_types' in root.attrib:
        white_listed_file_types = str(root.attrib['white_listed_file_types'])

    allow_multiple_files = True
    if 'allow_multiple_files' in root.attrib:
        allow_multiple_files = _parse_boolean(str(root.attrib['allow_multiple_files']))

    allow_latex = False
    if 'allow_latex' in root.attrib:
        allow_latex = _parse_boolean(str(root.attrib['allow_latex']))

    group_access = {}
    if 'group_access' in root.attrib:
        group_access = GroupAccessDict().from_json(json.loads(root.attrib['group_access']))

    show_rubric_during_response = False
    if 'show_rubric_during_response' in root.attrib:
        show_rubric_during_response = _parse_boolean(str(root.attrib['show_rubric_during_response']))

    # Retrieve the title
    title_el = root.find('title')
    if title_el is None:
        raise UpdateFromXmlError('Every assessment must contain a "title" element.')
    title = _safe_get_text(title_el)

    # Retrieve the rubric
    rubric_el = root.find('rubric')
    if rubric_el is None:
        raise UpdateFromXmlError('Every assessment must contain a "rubric" element.')
    rubric = parse_rubric_xml(rubric_el)

    # Retrieve the prompts
    prompts = _parse_prompts_xml(root)

    prompts_type = 'text'
    if 'prompts_type' in root.attrib:
        prompts_type = str(root.attrib['prompts_type'])

    # Retrieve the leaderboard if it exists, otherwise set it to 0
    leaderboard_show = 0
    if 'leaderboard_show' in root.attrib:
        try:
            leaderboard_show = int(root.attrib['leaderboard_show'])
        except (TypeError, ValueError) as ex:
            raise UpdateFromXmlError('The leaderboard must have an integer value.') from ex

    # Retrieve teams info
    teams_enabled = False
    selected_teamset_id = None
    if 'teams_enabled' in root.attrib:
        teams_enabled = _parse_boolean(str(root.attrib['teams_enabled']))
    if 'selected_teamset_id' in root.attrib:
        selected_teamset_id = str(root.attrib['selected_teamset_id'])

    # Retrieve the assessments
    assessments_el = root.find('assessments')
    if assessments_el is None:
        raise UpdateFromXmlError('Every assessment must contain an "assessments" element.')
    assessments = parse_assessments_xml(assessments_el)

    return {
        'title': title,
        'prompts': prompts,
        'prompts_type': prompts_type,
        'rubric_criteria': rubric['criteria'],
        'rubric_assessments': assessments,
        'rubric_feedback_prompt': rubric['feedbackprompt'],
        'rubric_feedback_default_text': rubric['feedback_default_text'],
        'submission_start': submission_start,
        'submission_due': submission_due,
        'text_response': text_response,
        'text_response_editor': text_response_editor,
        'file_upload_response': file_upload_response,
        'allow_file_upload': allow_file_upload,
        'file_upload_type': file_upload_type,
        'white_listed_file_types': white_listed_file_types,
        'allow_multiple_files': allow_multiple_files,
        'allow_latex': allow_latex,
        'group_access': group_access,
        'leaderboard_show': leaderboard_show,
        'teams_enabled': teams_enabled,
        'selected_teamset_id': selected_teamset_id,
        'show_rubric_during_response': show_rubric_during_response,
    }


def parse_from_xml_str(xml):
    """
    Create a dictionary for the OpenAssessment XBlock's content from an XML
    string definition. Parses the string using a library that avoids some known
    security vulnerabilities in etree.

    Args:
        xml (unicode): The XML definition of the XBlock's content.

    Returns:
        A dictionary of all configuration values for the XBlock.

    Raises:
        UpdateFromXmlError: The XML definition is invalid.
        InvalidRubricError: The rubric was not semantically valid.
        InvalidAssessmentsError: The assessments are not semantically valid.
    """
    return parse_from_xml(_unicode_to_xml(xml))


def _unicode_to_xml(xml):
    """
    Converts unicode string to XML node.

    Args:
        xml (unicode): The XML definition of some XBlock configuration.

    Raises:
        UpdateFromXmlError: Raised when the XML definition is invalid.

    """
    # Parse the XML content definition
    # Use the defusedxml library implementation to avoid known security vulnerabilities in ElementTree:
    # http://docs.python.org/2/library/xml.html#xml-vulnerabilities
    try:
        return safe_etree.fromstring(xml.encode('utf-8'))
    except (ValueError, safe_etree.ParseError) as ex:
        raise UpdateFromXmlError("An error occurred while parsing the XML content.") from ex


def parse_examples_from_xml_str(xml):
    """
    Converts an XML string of examples (Student Training or AI) into a dictionary
    representing the same information.

    Args:
        xml (unicode): The XML definition of the examples

    Returns
        (list of dict): The example definition
    """
    examples_root = _unicode_to_xml(xml)
    examples = examples_root.findall('example')
    return parse_examples_xml(examples)
