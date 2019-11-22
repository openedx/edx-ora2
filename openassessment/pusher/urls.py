""" Urls for pusher app. """
from __future__ import absolute_import

from django.conf.urls import url

from openassessment.pusher import views


urlpatterns = [
    url(
        r'^authenticate/$',
        views.authenticate
    ),
]
