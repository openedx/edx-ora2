from django.conf.urls import url

from openassessment.staff_grader.api import locks_view

urlpatterns = [
    # Enhanced Staff Grader (ESG) locking
    url(r'submission/(?P<submission_uuid>.+)/lock$', locks_view, name='openassessment-submission-lock')
]