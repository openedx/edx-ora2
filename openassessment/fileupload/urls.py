""" Urls for fileupload app. """


from django.conf.urls import url

from openassessment.fileupload import views_django_storage, views_filesystem

urlpatterns = [
    url(r'^django/(?P<key>.+)/$', views_django_storage.django_storage, name='openassessment-django-storage'),
    url(r'^(?P<key>.+)/$', views_filesystem.filesystem_storage, name='openassessment-filesystem-storage'),
]
