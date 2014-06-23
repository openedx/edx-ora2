"""
Test utilities
"""
from django.core.cache import cache
from django.test import TestCase
from openassessment.assessment.models.ai import (
    CLASSIFIERS_CACHE_IN_MEM, CLASSIFIERS_CACHE_IN_FILE
)


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
        CLASSIFIERS_CACHE_IN_MEM.clear()
        CLASSIFIERS_CACHE_IN_FILE.clear()
