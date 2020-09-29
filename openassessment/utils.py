"""
Utility functions
"""
import logging
from django.contrib.auth import get_user_model
from django.core.cache import cache

logger = logging.getLogger("ora.utils")


def anonymized_id_to_username(cls, anonymized_id):
    """
    Args:
        anonymized_id - an anonymized id.
    Returns:
        username - username mapped to the anonymized ID
    """
    User = get_user_model()

    cache_key = "anonymized.to.username.{}".format(anonymized_id)
    try:
        cached_username = cache.get(cache_key)
    except Exception:  # pylint: disable=broad-except
        # The cache backend could raise an exception
        # (for example, memcache keys that contain spaces)
        logger.exception("Error occurred while retrieving student item from the cache")
        cached_username = None

    if cached_username is not None:
        return cached_username
    else:
        try:
            username = cls._use_read_replica(  # pylint: disable=protected-access
                User.objects.filter(anonymoususerid__anonymous_user_id=anonymized_id)
            )[0].username

            cache.set(cache_key, username)
            return username
        except IndexError:
            return None
