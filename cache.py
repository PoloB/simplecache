
import weakref


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


class CacheClassType(object):
    """Main cache object.
    Each class that inherits from this class can cache the construction of its
    instances using the class method decorators.

    In order to make use of the cache, you must implements
    the following methods in the child class:

    - keys_names:
        This class method shall return the keys' name used for caching.

    - keys_from_inst:
        This instance method shall return the cache keys from the instance.

    Then, it is possible to use the following decorators on class method
    constructors:

    - cache_inst_from_key:
        The decorator returns the cached instance from the arguments of the
        decorated method if possible. Otherwise, it executes the decorated
        function, expecting the corresponding instance as returned value.
        You must always return a generator from the decorated function.


    - cache_inst_from_condition:

    """

    _kwd_mark = object()

    _container = CacheContainer
    _cache_content = {}
    _cache_for_second_id = weakref.WeakValueDictionary()
    _condition_cache = {}

    class InstanceNotValid(Exception):
        pass

    class CacheWrapper(object):

        def __init__(self, wrap_func):
            self._called = False
            self._wrap_func = wrap_func
            self._generator = wrap_func()

        def __iter__(self):
            self._called = True
            return self._wrap_func()

        def __getitem__(self, item):
            return list(self._wrap_func())[item]

        def __next__(self):
            return self._generator

        def __repr__(self):
            return list(self._wrap_func()).__repr__()

    @classmethod
    def delete_cache(cls):
        cls._condition_cache = {}
        cls._prim_id_for_second_id = weakref.WeakValueDictionary()
        cls._cache_content = {}

    @classmethod
    def keys_names(cls):
        """This method should a generator on keys of type string."""
        raise NotImplementedError()

    def keys_from_inst(self):
        """You must override this function to tell the cache how to
        get the cache key from an instance of the cache class.
        You must return a generator string.
        You must yield the keys of the instance in the same order as
        the CacheClassType.keys does.

        For example, if you define the
        class method CacheClassType.keys like this:

        @classmethod
        def keys(cls):
            for k in ['id', 'name']:
                yield k

        You shall define the keys_from_inst method like this:

        def keys_from_inst(self):
            for k in ['id', 'name']:
                yield getattr(self, k)
        """
        raise NotImplementedError()

    def get_cache_keys(self):
        """Returns a generator of the cache keys for this instance."""

        keys = self.keys_from_inst()
        cache_keys = self.keys_names()

        # Process primary id
        cache_keys.__next__()
        yield keys.__next__()

        # Do other keys
        for key in keys:
            ck = cache_keys.__next__()

            # If one of the sub index is None, we skip
            if key is None:
                continue

            yield self._add_class_name_to_key((ck, key))

    @classmethod
    def _add_class_name_to_key(cls, input_key):
        return cls.__name__, input_key

    @classmethod
    def __craft_key_with_args(cls, key, args, kwargs):
        """Craft the given key from the given args and kwargs."""

        args_key = (key, args + (cls._kwd_mark,) +
                    tuple(sorted(kwargs.items())))
        return args_key

    @classmethod
    def _insert_inst_in_cache(cls, inst):
        """Inserts the given instance in the cache.

        Args:
            inst (CacheClassType): instance to insert in the cache

        Returns:
            cls: instance from the cache.
        """

        # Get the keys from the result of the function
        if not isinstance(inst, cls):
            return inst

        keys = inst.get_cache_keys()

        # Caching using the primary key
        prim_key = cls._add_class_name_to_key(keys.__next__())

        # Make sure it's not in cache already
        if prim_key in cls._cache_content:
            return cls._cache_content[prim_key].content

        container = cls._container(inst)
        cls._cache_content[prim_key] = container

        # Add the other keys in the cache
        for k in keys:
            cls._cache_for_second_id[k] = container

        # Return the content of the cache
        return cls._cache_content[prim_key].content

    @classmethod
    def _remove_from_cache(cls, inst):

        # Get the keys from the result of the function
        keys = inst.get_cache_keys()

        # Get primary key
        prim_key = keys.__next()

        # Remove from main cache
        if prim_key in cls._cache_content:
            cls._cache_content.pop([prim_key])
        else:
            return

        # Add the other keys in the cache
        for k in keys:
            cls._cache_for_second_id.pop(k)

    @staticmethod
    def cache_inst_from_key(key):
        """Cache the decorated function using the given key.

        Args:
            key: key on which to cache

        Returns:
            instance
        """
        def decorator(func):
            def wrapper(cls, *args, **kwargs):
                # Craft the cache key from hashable inputs
                cache_key = cls.__craft_key_with_args(key, args, kwargs)
                keys = cls.keys_names()

                # Try to retrieve from cache
                if key != keys.__next__():
                    # It's a secondary key
                    second_key = cls._add_class_name_to_key((key, cache_key))

                    try:
                        cache_key = cls._cache_for_second_id[second_key]
                    except KeyError:
                        cache_key = None

                if cache_key in cls._cache_content:
                    return cls._cache_content[cache_key].content

                # We couldn't retrieve from cache, let's instantiate
                res = func(cls, *args, **kwargs)

                # Just return result
                if not isinstance(res, cls):
                    msg = "You must return an instance of type {0} from the " \
                          "function {1}".format(cls.__name__, func.__name__)
                    raise CacheClassType.InstanceNotValid(msg)

                return cls._insert_inst_in_cache(res)

            return wrapper

        return decorator

    @staticmethod
    def cache_inst_from_condition(func):
        def wrapper(cls, *args, **kwargs):

            def get():

                args_key = args + (cls._kwd_mark,) + \
                           tuple(sorted(kwargs.items()))
                input_function_key = (func.__name__, args_key)
                cache_key = cls._add_class_name_to_key(input_function_key)

                # Try to retrieve from cache
                if cache_key in cls._condition_cache:
                    list_prim_keys = cls._condition_cache[
                        cache_key]
                    for pk in list_prim_keys:
                        yield cls._cache_content[pk].content

                # We couldn't retrieve from cache, let's instantiate
                list_res = func(cls, *args, **kwargs)

                keys_to_cache = []

                # Get the keys from the result of the function
                for r in list_res:
                    # Appends the cached instance to the result
                    inst = cls._insert_inst_in_cache(r)
                    inst_prim_key = inst.get_cache_keys().__next__()
                    mod_key = cls._add_class_name_to_key(inst_prim_key)
                    keys_to_cache.append(mod_key)
                    yield inst

                # Add the condition to the cache
                cls._condition_cache[cache_key] = keys_to_cache
            return cls.CacheWrapper(get)
        return wrapper

    @staticmethod
    def insert(func):
        def wrapper(cls, *args, **kwargs):

            inst = func(cls, *args, **kwargs)

            if not inst:
                return inst

            inst = cls._insert_inst_in_cache(inst)

            # Invalidate the condition cache
            cls._condition_cache = {}

            return inst

        return wrapper

    @staticmethod
    def remove(func):
        def wrapper(self, *args, **kwargs):

            # Execute the function
            res = func(self, *args, **kwargs)

            # Remove from cache
            self._remove_from_cache(self)

            # Invalidate the condition cache
            self._condition_cache = {}

            return res

        return wrapper


class SessionCacheClassType(CacheClassType):

    @classmethod
    def keys_names(cls):
        raise NotImplementedError()

    def keys_from_inst(self):
        raise NotImplementedError()

    _prim_id_for_session_key = {}

    def __init__(self):
        self.__session_key__ = None

    @classmethod
    def from_session_id(cls, sid):
        try:
            second_key = cls._add_class_name_to_key(sid)
            prim_key = cls._prim_id_for_session_key[second_key]
            return cls._cache_content[prim_key].content
        except KeyError:
            return None

    def set_session_id(self, sid):

        k = self._add_class_name_to_key(sid)
        inst = self._insert_inst_in_cache(self)
        self.__session_key__ = k
        prim_key = inst.get_cache_keys().__next__()
        prim_key = self._add_class_name_to_key(prim_key)
        self._prim_id_for_session_key[k] = prim_key

    def remove_session_id(self):
        try:
            self._prim_id_for_session_key.pop(self.__session_key__)
        except KeyError:
            pass

        self.__session_key__ = None
