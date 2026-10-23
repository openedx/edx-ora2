"""
Provides the upload endpoint for the django storage backend.
"""


from django.contrib.auth.decorators import login_required
from django.shortcuts import HttpResponse
from django.views.decorators.http import require_http_methods

from .backends.django_storage import Backend


@login_required()
@require_http_methods(["PUT"])
def django_storage(request, key):
    """
    Upload files using django storage backend.
    """
    Backend().upload_file(key, request.body)
    return HttpResponse()
