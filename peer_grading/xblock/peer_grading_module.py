import logging
from x_module import XBlock
from xmodule.raw_module import RawDescriptor

log = logging.getLogger(__name__)


class PeerGradingFields(object):
    """
    @todo We'll need some Peer Grading Fields to define what information we want to pass to the grading workflow.
    """
    pass


class PeerGradingModule(PeerGradingFields, XBlock):

    _VERSION = 0


class PeerGradingDescriptor(PeerGradingFields, RawDescriptor):
    """
    Module for adding peer grading questions
    """
    # TODO What is a descriptor?
    pass
