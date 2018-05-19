

class CacheContainer(object):
    """This class is a container that stores cache content.
    This the class manipulated by the CacheManager."""

    def __init__(self, cache_content):
        self._content = cache_content

    @property
    def content(self):
        """Returns the content of the cache container."""
        return self._content


class ClassCacheManager(object):
    _kwd_mark = object()
    container = CacheContainer

    def __init__(self, keys, keys_from_cached_func):
        """Creates a cache manager."""

        self._enabled = True
        self._keys = keys
        self._cache_content = {}
        self._prim_id_for_second_id = {}
        self._condition_cache = {}
        self._keys_from_cached_func = keys_from_cached_func

    def craft_key(self, key, args, kwargs):

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

        # Get the keys from the result of the function
        keys = self._keys_from_cached_func(inst)

        # Caching using the primary key
        prim_key = keys[0]

        # Make sure it's not in cache already
        if prim_key in self._cache_content:
            return self._cache_content[prim_key].content

        self._cache_content[prim_key] = ClassCacheManager.container(inst)

        # Add the other keys in the cache
        for i, k in enumerate(keys[1:]):
            second_key = (self._keys[i + 1], k)
            self._prim_id_for_second_id[second_key] = prim_key

        # Return the content of the cache
        return self._cache_content[prim_key].content

    def cache_inst_from_key(self, key):
        def decorator(func):
            def wrapper(cls, *args, **kwargs):
                # Craft the cache key from hashable inputs
                cache_key = self.craft_key(key, args, kwargs)

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
        def decorator(func):
            def wrapper(cls, *args, **kwargs):

                class CacheCallWrapper(object):
                    @staticmethod
                    def get():
                        # Craft the cache key from hashable inputs
                        args_key = args + (ClassCacheManager._kwd_mark,) + \
                                   tuple(sorted(kwargs.items()))
                        cache_key = (func.__name__, args_key)

                        # Try to retrieve from cache
                        if cache_key in self._condition_cache:
                            list_prim_keys = self._condition_cache[cache_key].content
                            for pk in list_prim_keys:
                                yield self._cache_content[pk]

                        # We couldn't retrieve from cache, let's instantiate
                        list_res = func(cls, *args, **kwargs)

                        # Get the keys from the result of the function
                        for r in list_res:

                            # Appends the cached instance to the result
                            yield self._insert_inst_in_cache(r)

                return CacheCallWrapper
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
