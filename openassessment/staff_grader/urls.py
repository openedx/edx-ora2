"""
URLS for Enhanced Staff Grader (ESG)
"""
from django.conf.urls import url

from openassessment.staff_grader.api import locks_view

urlpatterns = [
    # Enhanced Staff Grader (ESG) locking
    url(r'api/submission/lock$', locks_view, name='submission-lock')
]
