"""
Togglable decorator used to display/hide openassessment units in mobile apps.
"""
from xblock.core import XBlock

from openassessment.xblock.config_mixin import ConfigMixin


class TogglableMobileSupport(ConfigMixin):
    """
    A class decorator used to enable/disable mobile support for
     openassessment units.
    """
    def __call__(self, view):
        """
        Add mobile support if the feature flag is enabled.
        """
        try:
            if self.is_mobile_support_enabled:
                return XBlock.supports('multi_device')(view)
        except ImportError:
            # Openedx libraries are not available in testing
            # environment.
            pass
        return view


togglable_mobile_support = TogglableMobileSupport()
