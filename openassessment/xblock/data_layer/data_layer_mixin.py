"""
Data layer for ORA

XBlock handlers which surface info about an ORA, instead of being tied to views.
"""
from xblock.core import XBlock

from openassessment.xblock.data_layer.serializers import OraBlockInfoSerializer


class DataLayerMixin:
    @XBlock.json_handler
    def get_block_info(self, data, suffix=""):
        context = {}
        block_info = OraBlockInfoSerializer(self, context=context)
        return block_info.data
