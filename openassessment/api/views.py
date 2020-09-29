import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.django import modulestore
from openassessment.data import OraAggregateData
import six
from openassessment.workflow.models import AssessmentWorkflow, TeamAssessmentWorkflow
from submissions import api as sub_api
from django.contrib.sites.models import Site
from django.urls import reverse
from openassessment.utils import anonymized_id_to_username


class SummariseAllAssesments(APIView):
    """
    View to list all tasks in a course.

    * Only staff users are able to access this view.
    """

    permission_classes = (IsAdminUser,)

    def get(self, request, course_id):
        """
        List ORA tasks in a course, along with their statistics.
        """

        responses = OraAggregateData.collect_ora2_responses(str(course_id))

        all_valid_ora_statuses = set()
        all_valid_ora_statuses.update(AssessmentWorkflow().STATUS_VALUES)
        all_valid_ora_statuses.update(TeamAssessmentWorkflow().STATUS_VALUES)

        openassessment_blocks = modulestore().get_items(
            CourseKey.from_string(course_id), qualifiers={'category': 'openassessment'}
        )
        # filter out orphaned openassessment blocks
        openassessment_blocks = {
            six.text_type(block.location): block for block in openassessment_blocks if block.parent is not None
        }

        result = {}
        parent_names = {}
        for location, block in openassessment_blocks.items():
            parent_str = six.text_type(block.parent)
            if location in responses.keys():
                result[location] = responses[location]
            else:
                result[location] = {key: 0 for key in all_valid_ora_statuses}

            if parent_str not in parent_names:
                parent_names[parent_str] = modulestore().get_item(block.parent).display_name
            result[location]['unit'] = parent_names[parent_str]

        return Response(result)


class ListWaitingAssessments(APIView):
    """
    List students that are waiting for some grade, and show a link to override it's grade.

    * Only staff users are able to access this view.
    """

    permission_classes = (IsAdminUser,)

    def get(self, request, course_id):
        """
        List all users waiting on grading and a link to override their grade.
        """

        result = []
        all_waiting_workflows = AssessmentWorkflow.objects.filter(course_id=course_id, status="waiting")

        for workflow in all_waiting_workflows:
            response = {}
            student_item = sub_api.get_submission_and_student(workflow.submission_uuid)['student_item']
            response['link'] = reverse(
                'jump_to',
                kwargs={
                    'course_id': student_item['course_id'],
                    'location': student_item['item_id'],
                },
            )
            response['username'] = anonymized_id_to_username(sub_api, student_item['student_id'])
            result.append(response)

        return Response(result)
