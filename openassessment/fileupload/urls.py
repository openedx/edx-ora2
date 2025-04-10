""" Urls for fileupload app. """

from django.urls import path

from openassessment.fileupload import views_django_storage, views_filesystem

urlpatterns = [
    path('django/<path:key>/', views_django_storage.django_storage,
         name='openassessment-django-storage'),
    path('<path:key>/', views_filesystem.filesystem_storage,
         name='openassessment-filesystem-storage'),
]
