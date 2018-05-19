

class CacheContainer(object):
    """This class is a container that stores cache content and other metadata.
    You may override this class to create new methods to access custom data.
    """

    def __init__(self, cache_content):
        self._content = cache_content

    @property
    def content(self):
        """Returns the content of the cache container."""
        return self._content


class ClassCache(object):
    """Main cache object. Each instance of this class provides decorators to
    cache the result of class methods.
    It's main purpose is to cache the instantiation process."""

    _kwd_mark = object()

    class CacheWrapper(object):

        def __init__(self, wrap_func):
            self._wrap_func = wrap_func

        def __iter__(self):
            return self._wrap_func()

        def __repr__(self):
            return list(self._wrap_func()).__repr__()

    def __init__(self, keys, keys_from_cached_instance,
                 container=CacheContainer):
        """Creates a cache manager.

        Args:
            keys (list of tuple): key tuple names of the instance.
                All the instance shall have a an unique value for each key.
            keys_from_cached_instance (func): function that returns the keys
                from an instance.
            container (class object): Class to use to store the cache."""

        self._container = container
        self._enabled = True
        self._keys = keys
        self._cache_content = {}
        self._prim_id_for_second_id = {}
        self._condition_cache = {}
        self._keys_from_cached_func = keys_from_cached_instance

    def _craft_key(self, key, args, kwargs):
        """Craft the given key from the given args and kwargs."""

        assert isinstance(key, tuple), (type(key), key)
        assert key in self._keys, (key, self._keys)

        tup = list()

        args_count = 0
        for k in key:

            if k in kwargs:
                tup.append(kwargs[k])

            else:
                tup.append(args[args_count])
                args_count += 1

        return tuple(tup)

    def _insert_inst_in_cache(self, inst):
        """Inserts the given instance in the cache.

        Args:
            inst (object): instance to insert in the cache

        Returns:
            object: instance from the cache.
        """

        # Get the keys from the result of the function
        keys = self._keys_from_cached_func(inst)

        # Caching using the primary key
        prim_key = keys[0]

        # Make sure it's not in cache already
        if prim_key in self._cache_content:
            return self._cache_content[prim_key].content

        self._cache_content[prim_key] = self._container(inst)

        # Add the other keys in the cache
        for i, k in enumerate(keys[1:]):
            second_key = (self._keys[i + 1], k)
            self._prim_id_for_second_id[second_key] = prim_key

        # Return the content of the cache
        return self._cache_content[prim_key].content

    def cache_inst_from_key(self, key):
        """Cache the decorated function using the given key.

        Args:
            key: key on which to cache

        Returns:
            instance
        """
        def decorator(func):
            def wrapper(cls, *args, **kwargs):
                # Craft the cache key from hashable inputs
                cache_key = self._craft_key(key, args, kwargs)

                # Try to retrieve from cache
                if key != self._keys[0]:
                    # It's a secondary key
                    cache_key = self._prim_id_for_second_id[(key, cache_key)]

                if cache_key in self._cache_content:
                    return self._cache_content[cache_key].content

                # We couldn't retrieve from cache, let's instantiate
                res = func(cls, *args, **kwargs)

                return self._insert_inst_in_cache(res)

            return wrapper

        return decorator

    def cache_inst_from_condition(self):
        """Conditional cache decorator.
        Wraps the result function call into a CacheWrapper object.
        Every call to the CacheWrapper.get() method will return
        the function result or the cache content if available.
        """

        def decorator(func):
            def wrapper(cls, *args, **kwargs):

                def get():

                    args_key = args + (ClassCache._kwd_mark,) + \
                               tuple(sorted(kwargs.items()))
                    cache_key = (func.__name__, args_key)

                    # Try to retrieve from cache
                    if cache_key in self._condition_cache:
                        list_prim_keys = self._condition_cache[
                            cache_key].content
                        for pk in list_prim_keys:
                            yield self._cache_content[pk]

                    # We couldn't retrieve from cache, let's instantiate
                    list_res = func(cls, *args, **kwargs)

                    # Get the keys from the result of the function
                    for r in list_res:
                        # Appends the cached instance to the result
                        yield self._insert_inst_in_cache(r)

                return ClassCache.CacheWrapper(get)
            return wrapper

        return decorator

    def insert(self):
        def decorator(func):
            def wrapper(cls, *args, **kwargs):

                inst = func(cls, *args, **kwargs)

                if not inst:
                    return inst

                inst = self._insert_inst_in_cache(inst)

                # Invalidate the condition cache
                self._condition_cache = {}

                return inst

            return wrapper
        return decorator


class CacheManager(object):
    """This class can manage a cache."""
