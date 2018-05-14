from repoze.lru import LRUCache


class CacheContainer(object):
    """This class is a container that stores cache content.
    This the class manipulated by the CacheManager."""
    def __init__(self, cache_content):
        self._content = cache_content

    @property
    def content(self):
        """Returns the content of the cache container."""
        return self._content


class CacheManager(object):

    kwd_mark = object()

    def __init__(self):
        """Creates a cache manager."""

        self._cache_content = {}

    def cache(self, hash_function=None):
        """If hash_function is provided it will be used to craft the cache key
        the inputs. If not, the craft key will be crafted considering all inputs
        are hashable objects."""
        def decorator(long_func):
            def wrapper(*args, **kwargs):

                # Craft the cache key from hashable inputs
                if hash_function:
                    key = hash_function(*args, **kwargs)
                else:
                    key = args + (CacheManager.kwd_mark,) + tuple(
                        sorted(kwargs.items()))
                cache_key = (long_func.__name__, key)

                # Try to retrieve from cache
                if cache_key in self._cache_content:
                    return self._cache_content[cache_key].content

                # We couldn't retrieve from cache, we have to do the long stuff
                my_precious = long_func(*args, **kwargs)

                # We create a container for the cache and cache it
                self._cache_content[cache_key] = CacheContainer(my_precious)

                return my_precious

            return wrapper
        return decorator

    def reset_cache(self):
        self._cache_content = {}

    def is_empty(self):
        if len(self._cache_content) == 0:
            return True
        return False

    def set_enabled(self, value):
        self._enabled = value


