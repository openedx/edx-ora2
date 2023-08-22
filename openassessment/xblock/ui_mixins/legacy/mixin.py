"""
Class to combine JSON handlers and views for easy import to Openassessmentblock
"""

from openassessment.xblock.ui_mixins.legacy.json_handlers import LegacyHandlersMixin
from openassessment.xblock.ui_mixins.legacy.views import LegacyViewMixin


class LegacyViewUIMixin(
    LegacyHandlersMixin,
    LegacyViewMixin,
):
    pass
