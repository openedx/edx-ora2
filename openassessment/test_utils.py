"""
Test utilities
"""
from django.core.cache import cache
from django.test import TestCase, TransactionTestCase
from openassessment.assessment.models.ai import (
    CLASSIFIERS_CACHE_IN_MEM, CLASSIFIERS_CACHE_IN_FILE
)


def _clear_all_caches():
    """Clear the default cache and any custom caches."""
    cache.clear()
    CLASSIFIERS_CACHE_IN_MEM.clear()
    CLASSIFIERS_CACHE_IN_FILE.clear()


class CacheResetTest(TestCase):
    """
    Test case that resets the cache before and after each test.
    """
    def setUp(self):
        super(CacheResetTest, self).setUp()
        _clear_all_caches()

    def tearDown(self):
        super(CacheResetTest, self).tearDown()
        _clear_all_caches()


class TransactionCacheResetTest(TransactionTestCase):
    """
    Transaction test case that resets the cache.
    """
    def setUp(self):
        super(TransactionCacheResetTest, self).setUp()
        _clear_all_caches()

    def tearDown(self):
        super(TransactionCacheResetTest, self).tearDown()
        _clear_all_caches()
