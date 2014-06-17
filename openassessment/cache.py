"""
In-memory cache implementations.
"""
import time
from django.core.cache import BaseCache
from django.utils.synch import RWLock


# Global variables shared by all `FastCache` instances
_CACHE = {}
_EXPIRE_INFO = {}
_LOCK = RWLock()


class FastCache(BaseCache):
    """
    A thread-safe, in-memory cache.  Django's in-memory cache implementation
    unfortunately pickles the objects it stores -- since we want
    to cache un-pickled objects, this doesn't help us!

    This uses a very simple cache invalidation scheme:
    clear the entire cache after a time limit is reached.
    """

    def __init__(self, params=None):
        """
        Create a new cache instance.  This shares state
        with all other `FastCache` instances.
        """
        if params is None:
            params = dict()

        super(FastCache, self).__init__(params)
        global _CACHE, _EXPIRE_INFO, _LOCK  # pylint: disable=W0602

        # Store local references to the global variables
        self._cache = _CACHE
        self._expire_info = _EXPIRE_INFO
        self._lock = _LOCK

        # We store a reference to a dictionary instead of to a timestamp
        # so we can modify the timestamp while referring to the same dictionary
        # shared with the other cache instances.
        if 'time' not in self._expire_info:
            self._expire_info['time'] = time.time() + self.default_timeout

    def get(self, key, default=None, version=None):
        """Retrieve a value from the cache."""
        key = self._make_and_validate_key(key, version)
        self._clear_if_expired()
        with self._lock.reader():
            return self._cache.get(key, default)

    def set(self, key, value, timeout=None, version=None):
        """Set a value in the cache."""
        key = self._make_and_validate_key(key, version)
        self._clear_if_expired()
        with self._lock.writer():
            self._cache[key] = value

    def clear(self):
        """Clear all values in the cache."""
        with self._lock.writer():
            self._cache.clear()
            self._expire_info['time'] = time.time() + self.default_timeout

    def add(self, key, value, timeout=None, version=None):
        raise NotImplementedError

    def _clear_if_expired(self):
        """Invalidate the cache if its expiration time has passed."""
        if time.time() > self._expire_info['time']:
            self.clear()

    def _make_and_validate_key(self, key, version):
        """Create a versioned key and validate it."""
        key = self.make_key(key, version=version)
        self.validate_key(key)
        return key


class TempCache(BaseCache):
    """
    An in-memory cache designed for temporary use (within a request).
    This does NOT share global state, so when the cache instance
    is garbage-collected, the contents of the cache can also
    be garbage-collected (assuming there are no other hard references
    to the values).

    This cache is NOT thread-safe.
    """
    def __init__(self):
        """Create a new cache instance."""
        super(TempCache, self).__init__({})
        self._cache = {}

    def get(self, key, default=None, version=None):
        """Retrieve a value from the cache."""
        return self._cache.get(key, default)

    def set(self, key, value, timeout=None, version=None):
        """Set a value in the cache."""
        self._cache[key] = value

    def clear(self):
        """Clear all values in the cache."""
        self._cache.clear()

    def add(self, key, value, timeout=None, version=None):
        raise NotImplementedError
