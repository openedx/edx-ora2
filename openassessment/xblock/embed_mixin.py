"""
The Embed Mixin renders views that might be embedded by other services like MFE.
"""


import json
import six

from django.urls import reverse
from django.conf import settings
from django.utils.translation import ugettext as _
from webob import Response
from xblock.core import XBlock
from openassessment.xblock.staff_area_mixin import require_course_staff


class EmbedMixin:
    """
    Implements instructor dashboard as standalone view and other
    utility methods to achieve that.
    """

    def _get_course(self):
        """
        Get course instance
        """
        from lms.djangoapps.courseware.courses import get_course_by_id
        return get_course_by_id(self.location.course_key)

    def _standalone_render(self, request, fragment, context=None):
        """
        Given a fragment return standalone response.
        """
        from common.djangoapps.edxmako.shortcuts import render_to_string
        from lms.djangoapps.course_home_api.utils import is_request_from_learning_mfe
        from openedx.core.lib.mobile_utils import is_request_from_mobile_app

        course = self._get_course()

        template = 'courseware/courseware-chromeless.html'

        # webob request doesn't have META which is request for
        # is_mobile_app and is_learning_mfe utility functions
        django_request = request._request

        render_context = {
            'fragment': fragment,
            'disable_accordion': True,
            'allow_iframing': True,
            'disable_header': True,
            'disable_footer': True,
            'disable_window_wrap': True,
            'course': course,
            'on_courseware_page': True,
            'is_learning_mfe': is_request_from_learning_mfe(django_request),
            'is_mobile_app': is_request_from_mobile_app(django_request),
        }

        # allow overriding render context
        if context:
            render_context.update(context)

        return Response(render_to_string(template, render_context), content_type='text/html', charset='UTF-8')

    @XBlock.handler
    @require_course_staff('STAFF_AREA')
    def embed_instructor_dashboard(self, request, suffix=''):  # pylint: disable=unused-argument
        """
        Standalone instructor dashboard.
        """
        from xmodule.modulestore.django import modulestore

        course = self._get_course()

        # find all open assessment blocks under the course
        openassessment_blocks = modulestore().get_items(
            self.location.course_key, qualifiers={'category': 'openassessment'}
        )

        # filter out orphaned openassessment blocks
        openassessment_blocks = [
            block for block in openassessment_blocks if block.parent is not None
        ]

        ora_items = []
        parents = {}

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
                'url_base': reverse('xblock_view', args=[course.id, block.location, 'student_view']),
                'url_grade_available_responses': reverse(
                    'xblock_view',
                    args=[course.id, block.location, 'grade_available_responses_view']
                ),
            })

        # create listing view fragment
        fragment = self.render('ora_blocks_listing_view', context={
            'ora_items': ora_items,
            'ora_item_view_enabled': settings.FEATURES.get('ENABLE_XBLOCK_VIEW_ENDPOINT', False)
        })

        return self._standalone_render(request, fragment)
