# -*- coding: utf-8 -*-
"""Middleware that adds a a log id to the request object.

Now any loggers in our call chain can include a globally unique id number for
this request in their output so that all the log events connected to any 
particular request can be connected back to one another.
"""


from uuid import uuid1 as uuid
from threading import current_thread
import logging


logger = logging.getLogger(__name__)


class SetRequestLogID(object):
    """This class gets instantiated via the Django settings.MIDDLEWARE_CLASSES"""
    # https://djangosnippets.org/snippets/2624/

    def process_request(self, request):
        """Attach UUID to request if it lacks one."""
        request_id = request.META.get('HTTP_X_EDX_LOG_TOKEN', False)
        if request_id:
            logger.debug("Incoming request preassigned %s" % request_id)
            return
        request_id = unicode(uuid())
        request.META['HTTP_X_EDX_LOG_TOKEN'] = request_id
        logger.debug("Incoming request assigned new id %s" % request_id)


class GlobalRequest(object):
    # https://djangosnippets.org/snippets/2853/
    _request_data = {}

    @staticmethod
    def get_request():
        try:
            return GlobalRequest._request_data[current_thread()]
        except KeyError:
            return None

    def process_request(self, request):
        thread = current_thread()
        GlobalRequest._request_data[thread] = request

    def process_response(self, request, response):
        """Destroy the thread data as we're generating our client response"""
        thread = current_thread()
        try:
            del GlobalRequest._request_data[thread]
        except KeyError:
            pass
        return response


def get_request():
    return GlobalRequest.get_request()


