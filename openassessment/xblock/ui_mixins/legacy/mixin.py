from .json_handlers import LegacyViewJSONHandlers
from .view import LegacyView

class LegacyViewUIMixin(LegacyViewJSONHandlers, LegacyView):
    pass
