# coding=utf-8
"""
Tests for in-memory cache implementations.
"""

import time
import itertools
from threading import Thread
from openassessment.test_utils import CacheResetTest
from openassessment.cache import FastCache, TempCache


class FastCacheTest(CacheResetTest):
    """
    Tests for the fast cache implementation.
    """
    def setUp(self):
        super(FastCacheTest, self).setUp()
        self.cache = FastCache()

    def test_single_thread(self):
        self.assertIs(self.cache.get(u'𝓽𝓮𝓼𝓽'), None)
        self.cache.set(u'𝓽𝓮𝓼𝓽', u'ѕυρєяƒℓу')
        self.assertEqual(self.cache.get(u'𝓽𝓮𝓼𝓽'), u'ѕυρєяƒℓу')
        self.cache.clear()
        self.assertIs(self.cache.get(u'𝓽𝓮𝓼𝓽'), None)

    def test_multiple_threads(self):
        def _thread(thread_num):
            """
            Set and get 100 keys in the cache.
            """
            for count in range(100):
                time.sleep(0.05)
                key = u"thread {thread_num}, key {key_num}".format(
                    thread_num=thread_num, key_num=count
                )
                self.cache.set(key, count)
                self.cache.get(key)

        # Start threads that set/get keys from the cache
        threads = [
            Thread(target=_thread, args=(thread_num,))
            for thread_num in range(20)
        ]
        for thread in threads:
            thread.start()

        # Wait for all the threads to finish
        for thread in threads:
            thread.join(300)

        # Verify that all the keys were set correctly
        expected_values = {
            u"thread {thread_num}, key {key_num}".format(
                thread_num=thread_num, key_num=key_num
            ): key_num
            for thread_num, key_num in itertools.product(range(5), range(100))
        }
        for key, value in expected_values.iteritems():
            self.assertEqual(self.cache.get(key), value)

    def test_multiple_threads_with_clear(self):
        def _thread():
            """
            Set and clear the cache.
            """
            for count in range(100):
                time.sleep(0.05)
                self.cache.set('test', count)
                self.cache.clear()

        # Start threads that set/clear the cache
        threads = [Thread(target=_thread) for _ in range(20)]
        for thread in threads:
            thread.start()

        # Wait for all threads to finish
        for thread in threads:
            thread.join(300)

        # Expect that the cache is empty
        self.assertIs(self.cache.get('test'), None)

    def test_expiration(self):
        # Artificially set the timeout to 0, so the cache
        # should be invalidated immediately
        self.cache.default_timeout = 0
        self.cache.clear()
        self.cache.set(u'𝕵𝖆𝖒𝖊𝖘 𝕭𝖗𝖔𝖜𝖓', u'ᴡɪᴛʜ ʜɪꜱ ᴏᴡɴ ʙᴀᴅ ꜱᴇʟꜰ')
        self.assertIs(self.cache.get(u'𝕵𝖆𝖒𝖊𝖘 𝕭𝖗𝖔𝖜𝖓'), None)


class TempCacheTest(CacheResetTest):
    """
    Tests for the temp cache implementation.
    """

    def setUp(self):
        super(TempCacheTest, self).setUp()
        self.cache = TempCache()

    def test_single_thread(self):
        self.assertIs(self.cache.get(u'𝓽𝓮𝓼𝓽'), None)
        self.cache.set(u'𝓽𝓮𝓼𝓽', u'ѕυρєяƒℓу')
        self.assertEqual(self.cache.get(u'𝓽𝓮𝓼𝓽'), u'ѕυρєяƒℓу')
        self.cache.clear()
        self.assertIs(self.cache.get(u'𝓽𝓮𝓼𝓽'), None)
