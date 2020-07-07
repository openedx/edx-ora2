"""
ORA APIs
"""

from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from edx_django_utils import monitoring as monitoring_utils
from django.urls import reverse
from opaque_keys.edx.keys import CourseKey

from openassessment.api import (
    get_open_assessment_blocks_for_course,
    retrieve_assessment_data,
)
from openassessment.serializers import OraAssesmentDataSerializer


class OpenAssesmentAggregatedData(RetrieveAPIView):
    """
    **Use Cases**

        Returns all ORA problems for a given course.

    **Example Requests**

        GET api/ora/v1/instructor_dashboard/assesment_data/{course_key}

    **Response Values**


    **Returns**

        * 200 on success with above fields.
        * 403 if the user is not authenticated.
        * 404 if the course is not available or cannot be seen.

    """

    permission_classes = (IsAuthenticated,)
    serializer_class = OraAssesmentDataSerializer
    queryset = []

    def get(self, request, *args, **kwargs):
        course_key_string = kwargs.get('course_id')
        course_key = CourseKey.from_string(course_key_string)

        ora_data = retrieve_assessment_data(course_key)

        serializer = self.get_serializer_class()(ora_data, many=True)
        return Response(serializer.data)
