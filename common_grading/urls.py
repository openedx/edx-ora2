from django.conf.urls import patterns, url, include
from rest_framework import routers


router = routers.DefaultRouter()

# Interface for communicating with the Peer Grading Module in LMS.
urlpatterns = patterns('',
                       url(r'^', include(router.urls)),
                       url(r'^peer_grading/', include('peer_grading.urls')),
                       url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
)