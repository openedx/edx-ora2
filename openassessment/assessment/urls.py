""" Assessment Urls. """
from __future__ import absolute_import

from django.conf.urls import url

from openassessment.assessment import views

urlpatterns = [
    url(
        r'^(?P<student_id>[^/]+)/(?P<course_id>[^/]+)/(?P<item_id>[^/]+)$',
        views.get_evaluations_for_student_item
    ),
]
