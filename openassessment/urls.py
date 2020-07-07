"""
Urls for base ORA API views.
"""
from django.conf import settings
from django.conf.urls import url

from openassessment.views.api import OpenAssesmentAggregatedData

urlpatterns = [
    url(
        r'^assessment_data/{course_id}/$'.format(course_id=settings.COURSE_ID_PATTERN),
        OpenAssesmentAggregatedData.as_view(),
        name='ora_aggregated_assessment_data'
    ),
]