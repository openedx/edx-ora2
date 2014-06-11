"""
Test utilities
"""
from django.core.cache import cache
from django.test import TestCase


class CacheResetTest(TestCase):
    """
    Test case that resets the cache before and after each test.
    """
    def setUp(self):
        super(CacheResetTest, self).setUp()
        cache.clear()

    def tearDown(self):
        super(CacheResetTest, self).tearDown()
        cache.clear()
