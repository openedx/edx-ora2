"""
Provides the pusher authentication endpoint.
"""
from __future__ import absolute_import

import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_http_methods

import pusher


_PUSHER_CLIENT = None


def pusher_client():
    global _PUSHER_CLIENT

    if not _PUSHER_CLIENT:
        _PUSHER_CLIENT = pusher.Pusher(
            app_id=settings.PUSHER_APP_ID,
            key=settings.PUSHER_KEY,
            secret=settings.PUSHER_SECRET,
        )

    return _PUSHER_CLIENT


@login_required()
@require_http_methods(["GET", "POST"])
def authenticate(request):
    """
    Authenticates a Pusher client.
    TODO: This shouldn't actually accept GET requests.
    """
    if request.method == 'GET':
        data = request.GET
    elif request.method == 'POST':
        data = request.POST
    else:
        return Http404('Method not allowed (yeah, yeah, I know, 405...')

    channel_name = data.get('channel_name', '')
    socket_id = data.get('socket_id', '')

    return JsonResponse(
        pusher_client().authenticate(
            channel=channel_name,
            socket_id=socket_id,
        )
    )
