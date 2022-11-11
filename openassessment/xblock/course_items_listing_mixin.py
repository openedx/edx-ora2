"""
The mixin with handlers for the course ora blocks listing view.

"""

from __future__ import absolute_import

import json

import six

from openassessment.xblock.staff_area_mixin import require_course_staff
from webob import Response
from xblock.core import XBlock


class CourseItemsListingMixin(object):
    """
    The mixin with handlers for the course ora blocks listing view.

    """

    @XBlock.handler
    @require_course_staff('STAFF_AREA')
    def get_ora2_responses(self, request, suffix=''):  # pylint: disable=unused-argument
        """
        Get information about all ora2 blocks in the course with response count for each step.

        """
        # Import is placed here to avoid model import at project startup.
        from openassessment.data import OraAggregateData
        responses = OraAggregateData.collect_ora2_responses(six.text_type(self.course_id))
        return Response(json.dumps(responses), content_type='application/json', charset='UTF-8')
