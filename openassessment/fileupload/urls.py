from django.conf.urls import patterns, url


urlpatterns = patterns('openassessment.fileupload.views_filesystem',
    url(r'^(?P<key>.+)/$', 'filesystem_storage', name='openassessment-filesystem-storage'),
)
