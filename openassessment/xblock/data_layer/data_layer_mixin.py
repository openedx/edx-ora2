"""
XBlock 
"""
from xblock.core import XBlock

class DataLayerMixin:

    @XBlock.json_handler
    def get_block_info(self, data, suffix=""):
        