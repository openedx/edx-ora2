""" A Mixin for authenticating Pusher clients. """
from __future__ import absolute_import, unicode_literals

import json
import logging

from django.conf import settings
from django.utils.functional import cached_property

from xblock.core import XBlock

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class PusherMixin(object):
    """
    Encapsulates all Pusher-related functionality.
    """
    @cached_property
    def pusher_client(self):
        return pusher.Pusher(
            app_id=settings.PUSHER_APP_ID,
            key=settings.PUSHER_KEY,
            secret=settings.PUSHER_SECRET,
        )

    @XBlock.json_handler
    def pusher_authenticate(self, channel_name, socket_id):
        return json.dumps(
            self.pusher_client.authenticate(
                channel=channel_name,
                socket_id=socket_id,
            )
        )
