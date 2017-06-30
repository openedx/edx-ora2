from django.conf.urls import patterns, url

urlpatterns = patterns(
    'openassessment.fileupload.views_django_storage',
    url(r'^django/(?P<key>.+)/$', 'django_storage', name='openassessment-django-storage'),
)

urlpatterns += patterns(
    'openassessment.fileupload.views_filesystem',
    url(r'^(?P<key>.+)/$', 'filesystem_storage', name='openassessment-filesystem-storage'),
)
