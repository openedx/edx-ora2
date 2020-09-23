""" API paths. """


from django.conf.urls import url

from openassessment.api import views

urlpatterns = [
    url(
        r'summarise/(?P<course_id>[^/]+)',
        views.SummariseAllAssesments.as_view()
    ),
    url(
        r'waiting/(?P<course_id>[^/]+)',
        views.ListWaitingAssessments.as_view()
    ),
]
