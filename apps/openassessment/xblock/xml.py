"""
Serialize and deserialize OpenAssessment XBlock content to/from XML.
"""
import lxml.etree as etree
import datetime as dt
import pytz
import dateutil.parser
import defusedxml.ElementTree as safe_etree
from django.utils.translation import ugettext as _


class UpdateFromXmlError(Exception):
    """
    Error occurred while deserializing the OpenAssessment XBlock content from XML.
    """
    pass


class InvalidRubricError(UpdateFromXmlError):
    """
    The rubric definition is semantically invalid.
    """
    pass


class InvalidAssessmentsError(UpdateFromXmlError):
    """
    The assessment definitions are not semantically valid.
    """
    pass


class InvalidDatesError(UpdateFromXmlError):
    """
    The start and due dates were not valid.
    """
    pass


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
    return sorted([
            el for el in items
            if isinstance(el, dict)
        ], key=lambda el: el.get('order_num', 0)
    )


def _safe_get_text(element):
    """
    Retrieve the text from the element, safely handling empty elements.

    Args:
        element (lxml.etree.Element): The XML element.

    Returns:
        unicode
    """
    return unicode(element.text) if element.text is not None else u""


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
        option_el.set('points', unicode(option.get('points', 0)))

        # Name (default to empty str)
        option_name = etree.SubElement(option_el, 'name')
        option_name.text = unicode(option.get('name', u''))

        # Explanation (default to empty str)
        option_explanation = etree.SubElement(option_el, 'explanation')
        option_explanation.text = unicode(option.get('explanation', u''))


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

        # Criterion name (default to empty string)
        criterion_name = etree.SubElement(criterion_el, u'name')
        criterion_name.text = unicode(criterion.get('name', ''))

        # Criterion prompt (default to empty string)
        criterion_prompt = etree.SubElement(criterion_el, 'prompt')
        criterion_prompt.text = unicode(criterion.get('prompt', u''))

        # Criterion options
        options_list = criterion.get('options', None)
        if isinstance(options_list, list):
            _serialize_options(criterion_el, options_list)


def _serialize_rubric(rubric_root, oa_block):
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
    # Rubric prompt (default to empty text)
    prompt = etree.SubElement(rubric_root, 'prompt')
    prompt.text = unicode(oa_block.prompt)

    # Criteria
    criteria_list = oa_block.rubric_criteria

    if isinstance(criteria_list, list):
        _serialize_criteria(rubric_root, criteria_list)


def _parse_date(date_str):
    """
    Attempt to parse a date string into ISO format (without milliseconds)
    Returns `None` if this cannot be done.

    Args:
        date_str (str): The date string to parse.

    Returns:
        unicode in ISO format (without milliseconds) if the date string is parseable
        None if parsing fails.
    """
    try:
        # Get the date into ISO format
        parsed_date = dateutil.parser.parse(unicode(date_str)).replace(tzinfo=pytz.utc)
        formatted_date = parsed_date.strftime("%Y-%m-%dT%H:%M:%S")
        return unicode(formatted_date)
    except (TypeError, ValueError):
        return None


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
            except ValueError:
                raise UpdateFromXmlError(_("XML option points must be an integer."))
        else:
            raise UpdateFromXmlError(_("XML option definition must contain a 'points' attribute."))

        # Option name
        option_name = option.find('name')
        if option_name is not None:
            option_dict['name'] = _safe_get_text(option_name)
        else:
            raise UpdateFromXmlError(_("XML option definition must contain a 'name' element."))

        # Option explanation
        option_explanation = option.find('explanation')
        if option_explanation is not None:
            option_dict['explanation'] = _safe_get_text(option_explanation)
        else:
            raise UpdateFromXmlError(_("XML option definition must contain an 'explanation' element."))

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
            raise UpdateFromXmlError(_("XML criterion definition must contain a 'name' element."))

        # Criterion prompt
        criterion_prompt = criterion.find('prompt')
        if criterion_prompt is not None:
            criterion_dict['prompt'] = _safe_get_text(criterion_prompt)
        else:
            raise UpdateFromXmlError(_("XML criterion definition must contain a 'prompt' element."))

        # Criterion options
        criterion_dict['options'] = _parse_options_xml(criterion)

        # Add the newly constructed criterion dict to the list
        criteria_list.append(criterion_dict)

    return criteria_list


def _parse_rubric_xml(rubric_root, validator):
    """
    Parse <rubric> element in the OpenAssessment XBlock's content XML.

    Args:
        rubric_root (lxml.etree.Element): The root of the <rubric> node in the tree.
        validator (callable): Function that accepts a rubric dict and returns
            a boolean indicating whether the rubric is semantically valid
            and an error message string.

    Returns:
        dict, a serialized representation of a rubric, as defined by the peer grading serializers.

    Raises:
        UpdateFromXmlError: The XML definition is invalid or the XBlock could not be updated.
        InvalidRubricError: The rubric was not semantically valid.
    """
    rubric_dict = dict()

    # Rubric prompt
    prompt_el = rubric_root.find('prompt')
    if prompt_el is not None:
        rubric_dict['prompt'] = _safe_get_text(prompt_el)
    else:
        raise UpdateFromXmlError(_("XML rubric definition must contain a 'prompt' element."))

    # Criteria
    rubric_dict['criteria'] = _parse_criteria_xml(rubric_root)

    # Validate the rubric
    success, msg = validator(rubric_dict)
    if not success:
        raise InvalidRubricError(msg)

    return rubric_dict


def _parse_assessments_xml(assessments_root, validator, start, due):
    """
    Parse the <assessments> element in the OpenAssessment XBlock's content XML.

    Args:
        assessments_root (lxml.etree.Element): The root of the <assessments> node in the tree.
        validator (callable): Function that accepts a list of assessment dictionaries and returns
            a boolean (indicating whether the assessment is semantically valid) and an error message.
        start (unicode): ISO-formatted date string representing the start time of the problem.
        due (unicode): ISO-formatted date string representing the due date of the problem.

    Returns:
        list of assessment dicts

    Raises:
        InvalidAssessmentsError: Assessment definitions were not semantically valid.
    """
    assessments_list = []

    prev_start = start
    for assessment in assessments_root.findall('assessment'):

        assessment_dict = dict()

        # Assessment name
        if 'name' in assessment.attrib:
            assessment_dict['name'] = unicode(assessment.get('name'))
        else:
            raise UpdateFromXmlError(_('XML assessment definition must have a "name" attribute'))

        # Assessment start
        if 'start' in assessment.attrib:
            parsed_start = _parse_date(assessment.get('start'))
            if parsed_start is not None:
                assessment_dict['start'] = parsed_start
            else:
                raise UpdateFromXmlError(_("Could not parse 'start' attribute as a valid date time"))
        else:
            # If no start is specified, default to the previous start date
            assessment_dict['start'] = prev_start

        # Assessment due
        if 'due' in assessment.attrib:
            parsed_start = _parse_date(assessment.get('due'))
            if parsed_start is not None:
                assessment_dict['due'] = parsed_start
            else:
                raise UpdateFromXmlError(_("Could not parse 'due' attribute as a valid date time"))
        else:
            # If no due date is specified, leave it as None for now
            # We will fill it in later when reverse-iterating through the assessments
            assessment_dict['due'] = None

        # Assessment must_grade
        if 'must_grade' in assessment.attrib:
            try:
                assessment_dict['must_grade'] = int(assessment.get('must_grade'))
            except ValueError:
                raise UpdateFromXmlError(_('Assessment "must_grade" attribute must be an integer.'))

        # Assessment must_be_graded_by
        if 'must_be_graded_by' in assessment.attrib:
            try:
                assessment_dict['must_be_graded_by'] = int(assessment.get('must_be_graded_by'))
            except ValueError:
                raise UpdateFromXmlError(_('Assessment "must_be_graded_by" attribute must be an integer.'))

        # Store the current start
        prev_start = assessment_dict['start']

        # Update the list of assessments
        assessments_list.append(assessment_dict)

    # Reverse through the list to fill in missing due dates
    prev_due = due
    for assessment_dict in reversed(assessments_list):
        if assessment_dict['due'] is None:
            assessment_dict['due'] = prev_due
        prev_due = assessment_dict['due']

    # Validate the semantics of the assessment definitions
    success, msg = validator(assessments_list)
    if not success:
        raise InvalidAssessmentsError(msg)

    return assessments_list


DISTANT_FUTURE = dt.datetime(dt.MAXYEAR, 1, 1).replace(tzinfo=pytz.utc)

def _latest_submission_due(deadlines):
    """
    Return the latest date that a submission can be due, which equals
    the earliest due date among problem and assessment deadlines.

    Args:
        deadlines (list of str): List of ISO-formatted date strings representing the due dates
            of problem, submission, and assessments.  Values of None indicate no deadline.

    Returns:
        ISO-formatted date string or None
    """
    # If no deadlines are set at all, default to no submission deadline.
    # Note that if *any* deadlines are set, then the submission must have a deadline,
    # since submissions happen before any assessments (and, trivially, before the problem closes).
    if all([val is None for val in deadlines]):
        return None
    else:
        parse = lambda date_str: dateutil.parser.parse(date_str).replace(tzinfo=pytz.utc) \
            if date_str is not None else DISTANT_FUTURE
        return min([parse(due) for due in deadlines]).isoformat()


def serialize_content(oa_block):
    """
    Serialize the OpenAssessment XBlock's content to XML.

    Args:
        oa_block (OpenAssessmentBlock): The open assessment block to serialize.

    Returns:
        xml (unicode)
    """
    root = etree.Element('openassessment')

    # Set submission due date
    if oa_block.submission_due is not None:
        root.set('submission_due', unicode(oa_block.submission_due))

    # Open assessment displayed title
    title = etree.SubElement(root, 'title')
    title.text = unicode(oa_block.title)

    # Assessment list
    assessments_root = etree.SubElement(root, 'assessments')
    for assessment_dict in oa_block.rubric_assessments:

        assessment = etree.SubElement(assessments_root, 'assessment')

        # Set assessment attributes, defaulting to empty values
        assessment.set('name', unicode(assessment_dict.get('name', '')))

        if 'must_grade' in assessment_dict:
            assessment.set('must_grade', unicode(assessment_dict['must_grade']))

        if 'must_be_graded_by' in assessment_dict:
            assessment.set('must_be_graded_by', unicode(assessment_dict['must_be_graded_by']))

        if 'start' in assessment_dict and assessment_dict['start'] is not None:
            assessment.set('start', unicode(assessment_dict['start']))

        if 'due' in assessment_dict and assessment_dict['due'] is not None:
            assessment.set('due', unicode(assessment_dict['due']))

    # Rubric
    rubric_root = etree.SubElement(root, 'rubric')
    _serialize_rubric(rubric_root, oa_block)

    # Return a UTF-8 representation of the XML
    return etree.tostring(root, pretty_print=True, encoding='utf-8')


DEFAULT_VALIDATOR = lambda *args: (True, '')

def update_from_xml(
    oa_block, root,
    rubric_validator=DEFAULT_VALIDATOR,
    assessments_validator=DEFAULT_VALIDATOR,
    dates_validator=DEFAULT_VALIDATOR,
):
    """
    Update the OpenAssessment XBlock's content from an XML definition.

    We need to be strict about the XML we accept, to avoid setting
    the XBlock to an invalid state (which will then be persisted).

    Args:
        oa_block (OpenAssessmentBlock): The open assessment block to update.
        root (lxml.etree.Element): The XML definition of the XBlock's content.

    Kwargs:
        rubric_validator (callable): Function that accepts a rubric dict and returns
            a boolean indicating whether the rubric is semantically valid and an error message.
            The default implementation performs no validation.
        assessments_validator (callable): Function that accepts a list of assessment dictionaries and returns
            a boolean (indicating whether the assessments are semantically valid) and an error message.
            The default implementation performs no validation.
        dates_validator (callable): Function of the form (start, due, date_ranges) --> (bool, str)
            where `start` and `due` are the start/due dates of the problem, and
            `date_ranges` is a list of `(start, due)` tuples for each component.
            The return values have the same meaning as the other validators.

    Returns:
        OpenAssessmentBlock

    Raises:
        UpdateFromXmlError: The XML definition is invalid or the XBlock could not be updated.
        InvalidRubricError: The rubric was not semantically valid.
        InvalidAssessmentsError: The assessments are not semantically valid.
    """

    # Check that the root has the correct tag
    if root.tag != 'openassessment':
        raise UpdateFromXmlError(_("XML content must contain an 'openassessment' root element."))

    # Retrieve the due date for the submission
    # (assume that the start date of submission is the same as the start date of the problem)
    # Set it to None by default; we will update it to the earliest deadline later on
    submission_due = None
    if 'submission_due' in root.attrib:
        submission_due = _parse_date(unicode(root.attrib['submission_due']))
        if submission_due is None:
            raise UpdateFromXmlError(_("Invalid date format for submission due date"))

    # Retrieve the title
    title_el = root.find('title')
    if title_el is None:
        raise UpdateFromXmlError(_("XML content must contain a 'title' element."))
    else:
        title = _safe_get_text(title_el)

    # Retrieve the rubric
    rubric_el = root.find('rubric')
    if rubric_el is None:
        raise UpdateFromXmlError(_("XML content must contain a 'rubric' element."))
    else:
        rubric = _parse_rubric_xml(rubric_el, rubric_validator)

    # Retrieve the assessments
    assessments_el = root.find('assessments')
    if assessments_el is None:
        raise UpdateFromXmlError(_("XML content must contain an 'assessments' element."))
    else:
        assessments = _parse_assessments_xml(assessments_el, assessments_validator, oa_block.start, oa_block.due)

    # If an assessment provides a due date, and a submission due date is not provided,
    # then the submission due date should default to the earliest assessment deadline.
    if submission_due is None:
        submission_due = _latest_submission_due([oa_block.due] + [asmnt['due'] for asmnt in assessments])

    # Validate the dates
    date_ranges = [(oa_block.start, submission_due)] + [(asmnt['start'], asmnt['due']) for asmnt in assessments]
    valid, msg = dates_validator(oa_block.start, oa_block.due, date_ranges)
    if not valid:
        raise InvalidDatesError(msg)

    # If we've gotten this far, then we've successfully parsed the XML
    # and validated the contents.  At long last, we can safely update the XBlock.
    oa_block.title = title
    oa_block.prompt = rubric['prompt']
    oa_block.rubric_criteria = rubric['criteria']
    oa_block.rubric_assessments = assessments
    oa_block.submission_due = submission_due

    return oa_block


def update_from_xml_str(oa_block, xml, **kwargs):
    """
    Update the OpenAssessment XBlock's content from an XML string definition.
    Parses the string using a library that avoids some known security vulnerabilities in etree.

    Args:
        oa_block (OpenAssessmentBlock): The open assessment block to update.
        xml (unicode): The XML definition of the XBlock's content.

    Kwargs:
        Same as `update_from_xml`

    Returns:
        OpenAssessmentBlock

    Raises:
        UpdateFromXmlError: The XML definition is invalid or the XBlock could not be updated.
        InvalidRubricError: The rubric was not semantically valid.
        InvalidAssessmentsError: The assessments are not semantically valid.
    """
    # Parse the XML content definition
    # Use the defusedxml library implementation to avoid known security vulnerabilities in ElementTree:
    # http://docs.python.org/2/library/xml.html#xml-vulnerabilities
    try:
        root = safe_etree.fromstring(xml.encode('utf-8'))
    except (ValueError, safe_etree.ParseError):
        raise UpdateFromXmlError(_("An error occurred while parsing the XML content."))

    return update_from_xml(oa_block, root, **kwargs)
