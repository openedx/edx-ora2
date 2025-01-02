""" Assessment Urls. """

from django.urls import re_path

from openassessment.assessment import views

urlpatterns = [
    re_path(
        r'^(?P<student_id>[^/]+)/(?P<course_id>[^/]+)/(?P<item_id>[^/]+)$',
        views.get_evaluations_for_student_item
    ),
]
