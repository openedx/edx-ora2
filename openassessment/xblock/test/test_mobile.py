""" Tests mobile support. """

from unittest import mock
from django.test import TestCase

from openassessment.xblock.mobile import togglable_mobile_support


class MobileSupportTest(TestCase):
    """ Test mobile support decorator. """

    @mock.patch('xblock.core.XBlock.supports')
    @mock.patch(
        'openassessment.xblock.config_mixin.ConfigMixin.is_mobile_support_enabled',
        new_callable=mock.PropertyMock
    )
    def test_mobile_support_enabled(self, config_mixin_mock, xblock_mock):
        """
        Test that when mobile support feature flag is enabled, the
        XBlock decorator gets called.
        """
        some_function = mock.Mock()
        config_mixin_mock.return_value = True
        xblock_decorator = mock.Mock()
        xblock_mock.return_value = xblock_decorator

        togglable_mobile_support(some_function)

        xblock_mock.assert_called_once_with('multi_device')
        xblock_decorator.assert_called_once_with(some_function)

    @mock.patch('xblock.core.XBlock.supports')
    @mock.patch(
        'openassessment.xblock.config_mixin.ConfigMixin.is_mobile_support_enabled',
        new_callable=mock.PropertyMock
    )
    def test_mobile_support_disabled(self, config_mixin_mock, xblock_mock):
        """
        Test that when mobile support feature flag is not enabled, the
        XBlock decorator does not get called.
        """
        some_function = mock.Mock()
        config_mixin_mock.return_value = False

        togglable_mobile_support(some_function)

        xblock_mock.assert_not_called()
