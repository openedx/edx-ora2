"""
RESTful interface for all Peer Grading Workflow. Covers all requests made for Peer Grading.
"""
import json
import logging
from django.http import HttpResponse

log = logging.getLogger(__name__)

_INTERFACE_VERSION = 0


def submit_peer_essay(request):
    response = {'version': _INTERFACE_VERSION,
                'success': True,
                'message': "Nothing happened."}
    return HttpResponse(json.dumps(response), mimetype="application/json")
