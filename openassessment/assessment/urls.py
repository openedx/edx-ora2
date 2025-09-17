""" Assessment Urls. """

from django.urls import path

from openassessment.assessment import views

urlpatterns = [
    path(
        '<str:student_id>/<str:course_id>/<str:item_id>',
        views.get_evaluations_for_student_item
    ),
]
