"""
Open Response Assesments APIs - Internal Python APIs
"""
import six
from django.urls import reverse

from xmodule.modulestore.django import modulestore

from openassessment.data import OraAggregateData


def get_open_assessment_blocks_for_course(course_key):
    """
    Returns all open assesment blocks from the modulestore
    """
    openassessment_blocks = modulestore().get_items(
        course_key, qualifiers={'category': 'openassessment'}
    )

    # filter out orphaned openassessment blocks
    openassessment_blocks = [
        block for block in openassessment_blocks if block.parent is not None
    ]

    return openassessment_blocks


def retrieve_assessment_data(course_key):
    """
    Return all formatted data to Open Responses section on Instructor Dashboard.
    """
    ora_items = []
    parents = {}
    course_key_str = six.text_type(course_key)

    # Retrieve aggregated response data for course.
    responses = OraAggregateData.collect_ora2_responses(course_key_str)

    # Retrieve all `openassesment` block's metadata
    openassessment_blocks = get_open_assessment_blocks_for_course(course_key)

    # Loop over each block and aggregate data
    for block in openassessment_blocks:
        block_parent_id = six.text_type(block.parent)
        result_item_id = six.text_type(block.location)
        if block_parent_id not in parents:
            parents[block_parent_id] = modulestore().get_item(block.parent)
        assessment_name = _("Team") + " : " + block.display_name if block.teams_enabled else block.display_name
        ora_items.append({
            'id': result_item_id,
            'name': assessment_name,
            'parent_id': block_parent_id,
            'parent_name': parents[block_parent_id].display_name,
            'staff_assessment': 'staff-assessment' in block.assessment_steps,
            # Append aggregated reponse data to each item
            'responses': responses[result_item_id]
        })

    return ora_items