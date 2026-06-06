import time


_cache = {}


def get_cache(key):
    """
    Get cached value if it exists and has not expired.
    """

    item = _cache.get(key)

    if item is None:
        return None

    value, expiry = item

    if time.time() > expiry:
        _cache.pop(key, None)
        return None

    return value


def set_cache(key, value, ttl=3600):
    """
    Store value in cache with expiry time.
    Default TTL = 1 hour.
    """

    if not key or value is None:
        return

    expiry = time.time() + ttl

    _cache[key] = (value, expiry)


def clear_cache():
    """
    Clear full cache manually if needed.
    """

    _cache.clear()


def cache_size():
    """
    Return number of active cached items.
    """

    return len(_cache)