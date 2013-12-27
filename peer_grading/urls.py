from django.conf.urls import patterns, url, include
from rest_framework import routers
from peer_grading.views import PeerGradedEssayViewSet, PeerGradingStatusViewSet


router = routers.DefaultRouter()
router.register(r'peergradedessay', PeerGradedEssayViewSet)
router.register(r'peergradingstatus', PeerGradingStatusViewSet)

# Interface for communicating with the Peer Grading Module in LMS.
urlpatterns = patterns('',
                       url(r'^', include(router.urls)),
                       url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework'))
)
