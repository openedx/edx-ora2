from .json_handlers import LegacyViewJSONHandlersMixin
from .views import LegacyViewMixin


class LegacyViewUIMixin(LegacyViewJSONHandlersMixin, LegacyViewMixin):
    pass
