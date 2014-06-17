"""
Test utilities
"""
from django.core.cache import cache, get_cache
from django.test import TestCase


class CacheResetTest(TestCase):
    """
    Test case that resets the cache before and after each test.
    """
    def setUp(self):
        super(CacheResetTest, self).setUp()
        self._clear_all_caches()

    def tearDown(self):
        super(CacheResetTest, self).tearDown()
        self._clear_all_caches()

    def _clear_all_caches(self):
        """
        Clear the default cache and any custom caches.
        """
        cache.clear()
        get_cache(
            'django.core.cache.backends.locmem.LocMemCache',
            LOCATION='openassessment.ai.classifiers_dict'
        ).clear()
