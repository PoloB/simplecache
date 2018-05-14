import datetime
from threading import Thread, Event

from log import log


class CacheRefresher(Thread):
    """Defines a thread that periodically calls the delete_cache class method
    of the cls class object it supervises.

    Args:
        cls (class object): the class for which to call the
            delete_cache class method.
        interval (int): interval of time between two deletion of the cache.
            Expressed in minutes."""

    def __init__(self, cls, interval, *args, **kwargs):
        Thread.__init__(self)
        self.interval = interval
        self._class = cls
        self.args = args
        self.kwargs = kwargs
        self.finished = Event()

    def cancel(self):
        """Stop the timer if it hasn't finished yet"""
        self.finished.set()

    def run(self):

        if self.interval:
            while not self.finished.wait(self.interval * 60):
                log.info("Cleaning {0} cache".format(self._class.__name__))
                self._class.delete_cache(*self.args, **self.kwargs)

        else:
            pass

    def reset(self):
        """ Reset the timer """
        self.finished.clear()


class CacheManager(object):

    def __init__(self, keys):
        """Creates a cache manager using the given indexes

        Args:
            keys"""

        assert isinstance(keys, list), (type(keys), keys)

        self.primary_key = keys[0]
        self.other_keys = keys[1:]
        self.lambda_func_keys = []

        self._cache_content = {}
        self._prim_key_by_other_key = {}

    def cache(self, cache_key, cache_key_from_input, keys_dict_from_result):
        def decorator(long_func):
            def wrapper(*args, **kwargs):
                # Check if the key is in the cache
                k = cache_key_from_input(args, kwargs)

                if cache_key == self.primary_key:
                    if k in self._cache_content:
                        return self._cache_content[k]

                elif cache_key in self.other_keys:
                    key = (cache_key, k)
                    if key in self._prim_key_by_other_key:
                        return self._cache_content[
                            self._prim_key_by_other_key[key]]
                else:
                    assert False, "The cache_key given is not a valid key."

                # We couldn't retrieve from cache, we have to do the long stuff
                my_precious = long_func(*args, **kwargs)

                # Retrieve the key for the cache
                keys = keys_dict_from_result(my_precious)
                try:
                    prim_key = keys[self.primary_key]
                except KeyError:
                    assert False, "No primary key in result."

                self._cache_content[prim_key] = my_precious

                for key in keys:
                    if key in self.other_keys:
                        self._prim_key_by_other_key[(key, keys[key])] = prim_key

                return my_precious

            return wrapper
        return decorator

    def reset_cache(self):
        self._cache_content = {}
        self._prim_key_by_other_key = {}

    def delete(self, prim_key):
        if prim_key in self._cache_content:
            self._cache_content.pop(prim_key)
            for k in self._prim_key_by_other_key.keys():
                v = self._prim_key_by_other_key[k]
                if v == prim_key:
                    self._prim_key_by_other_key.pop(k)

    def remove_second_key(self, second_key, second_key_value):

        full_key = (second_key, second_key_value)
        if full_key in self.other_keys:
            self._prim_key_by_other_key.pop(full_key)

    def is_empty(self):
        if len(self._cache_content) == 0:
            return True
        return False

    def set_enabled(self, value):
        self._enabled = value


class CacheAttr(object):
    """Utility class for caching instances of classes.
    Its purpose is to cache instance that takes time to instantiate.

    This class

    The cached decorator will try to return the cached instance using the
    decorated function arguments. If it is not available, the cache will
    execute the decorated function to get the attributes value.
    The cached decorator must be used on a class method constructor and provide
    the argument names that the decorated function will receive:

        >>> class MyCachedClass(CacheAttr):
        >>>     @classmethod
        >>>     @CacheAttr.cached('my_first_id')
        >>>     def construct_from_first_id(cls, first_id)
        >>>         result = my_long_function(first_id)
        >>>         return {'my_first_id': first_id, 'data': result}

    The decorated function will then return the instance as defined by the
    _instance method.

    The decorator handles both dict and list of dict.
    This below examples will then return a list of instance as defined by the
    _instance method.

        >>> class MyCachedClass(CacheAttr):
        >>>     @classmethod
        >>>     @CacheAttr.cached('my_first_id')
        >>>     def construct_from_multiple_first_id(cls, list_first_id)
        >>>         list_result = my_long_function(list_first_id)
        >>>         return [{'first_id': f_id, 'data': list_result[k]}
        >>>                 for k, f_id in enumerate(list_first_id)]

    The add_cache decorator will add the returned data to the cache
    after instantiation. The first id must be returned in the dict
    (or list of dict)

        >>> class MyCachedClass(CacheAttr):
        >>>     @classmethod
        >>>     @CacheAttr.add_cache
        >>>     def create_element(cls, some_inputs)
        >>>         list_result = my_long_function(list_first_id)
        >>>         return [{'first_id': f_id, 'data': list_result[k]}
        >>>                 for k, f_id in enumerate(list_first_id)]

    The update_cache decorator will update the value in the cache.
    It shall be used on instance methods.

        >>> class MyCachedClass(CacheAttr):
        >>>     @CacheAttr.update_cache
        >>>     def change_value(self, value)
        >>>         d = self.as_dict()
        >>>         d['value'] = value
        >>>         return self.as_dict()
    """

    # Caching
    __cache_indexes__ = ['id', 'second_id']  # Shall be unique in time
    __session_index__ = 'sid'
    __id_for_second_id__ = {}  # Associates secondary ids to the first one
    __id_for_session_id__ = {}  # Stores the first id for session_id
    __inst_cache__ = {}  # Stores the instances

    # Cleaning Thread
    __refresh_time__ = None  # in minutes
    __refresh_thread__ = None
    __cache_active__ = True
    __cache_size_limit__ = None

    def __init__(self, data, *args, **kwargs):
        self._data = data
        self.__last_demand = datetime.datetime.now()
        self._session_id = None

    def __repr__(self):

        uid = self._data[self.__class__.__cache_indexes__[0]]
        second_id = ""

        if len(self.__cache_indexes__) > 1:
            second_id = " " + self._data[self.__class__.__cache_indexes__[1]]

        return "[{0}#{1}]{2}".format(self.__class__.__name__, uid, second_id)

    def as_dict(self):
        return self._data

    @classmethod
    def check_cache(cls):
        if cls.__name__ not in cls.__inst_cache__:
            cls.__inst_cache__[cls.__name__] = {}

    @classmethod
    def get_cache(cls):
        cls.check_cache()
        return cls.__inst_cache__[cls.__name__]

    @classmethod
    def start_cleaning_thread(cls):
        """Starts a cleaning cache thread."""
        cls.__refresh_thread__ = CacheRefresher(cls, cls.__refresh_time__)
        cls.__refresh_thread__.start()

    @classmethod
    def limit_memory_size(cls, size, free_percent):
        """Limits the usage of memory to the size argument.
        This affects all the instances cached.
        When inserting in the cache being full, a percentage of free_percent
        of the instances in memory will be freed to continue the insertion.
        Increasing the free_percent value will require less time in checking the
        cache size (improving caching speed) but may require to update the cache
        more often.
        The instance not called for the longest time will be removed first when
        freeing memory.

        Args:
            size (int): size of the allowed memory for caching in bytes
            free_percent (float): percentage of instances freed when the cache
                threshold has been reached.
        """
        cls.__cache_size_limit__ = size
        


    @classmethod
    def active_cache(cls, value):
        """Enables or not the retrieval from cache by the functions decorated
        using the cached method."""
        cls.__cache_active__ = bool(value)

    @classmethod
    def delete_cache(cls, first_id=None, sid=None):
        """Delete the cache for the given first_id or session_id.
        If no inputs are provided, all the cache is reset."""

        if not first_id and not sid:
            cls.__inst_cache__[cls.__name__] = {}
            cls.__id_for_session_id__[cls.__name__] = {}
        elif first_id:
            cls.check_cache()
            if first_id in cls.__inst_cache__[cls.__name__].keys():
                cls.__inst_cache__[cls.__name__].pop(first_id)
            elif first_id in cls.__id_for_second_id__.keys():
                cls.__inst_cache__[cls.__name__].pop(
                    cls.__id_for_second_id__[first_id])
        elif sid:
            cls.__inst_cache__[cls.__name__].pop(cls.__id_for_session_id__[sid])

    def remove_session_cache(self):
        """Remove the instance from the cache."""
        try:
            self.__id_for_session_id__.pop(self._session_id)
        except KeyError:
            pass

    @classmethod
    def instantiate(cls, data):
        """Functions called right after retrieving data from the function
        decorated by the cached or add_cache method.
        It also creates attributes based on the name of the key values in data.

        You might overload this function to do fancy stuff during the
        instantiation process.

        Args:
            data (dict): data containing the dict.

        Returns:
            instance of class
        """

        prim_key = cls.__cache_indexes__[0]
        prim_id = data[prim_key]

        # Instantiate
        inst = cls(data)

        # Set the attributes
        setattr(inst, prim_key, data[prim_key])
        for sk in data.keys():
            if sk in cls.__cache_indexes__[1:]:
                cls.__id_for_second_id__[data[sk]] = prim_id
            setattr(inst, sk, data[sk])
        return inst

    @staticmethod
    def cached(*dargs):
        """decorator that returns the given values
        if they exits in the cache.
        Make sure to use parenthesis when using the decorator."""

        def real_decorator(func):
            # noinspection PyProtectedMember
            def wrapper(cls, *args, **kwargs):

                # Returns instance if not cache
                if not cls.__cache_active__:
                    data = func(cls, *args, **kwargs)
                    if data:
                        return cls.instantiate(data)
                    else:
                        return None

                # Try from the provided arguments
                for k, index in enumerate(dargs):

                    if index != cls.__cache_indexes__[0]:
                        # It's not the first index
                        # We try to get it from lookup table
                        try:
                            key = cls.__id_for_second_id__[(index, args[k])]
                        except KeyError:
                            continue
                    else:
                        # It's the first key
                        key = args[k]

                    # Try to retrieve from cache
                    try:
                        inst = cls.__inst_cache__[cls.__name__][key]
                        inst.__last_demand = datetime.datetime.now()
                        log.debug("Returned from cache!")
                        return inst  # Good job!
                    except KeyError:
                        pass

                # Query the value
                log.debug("Cache Missed...")
                data = func(cls, *args, **kwargs)

                if not data:
                    return None

                if not isinstance(data, list):
                    data = [data]

                insts = []

                for d in data:
                    inst = cls.instantiate(d)

                    prim_key = cls.__cache_indexes__[0]
                    prim_id = d[prim_key]

                    inst.__last_demand = datetime.datetime.now()
                    cls.check_cache()
                    cls.__inst_cache__[cls.__name__][prim_id] = inst
                    insts.append(inst)

                    # Create the second_id relation
                    for k in cls.__cache_indexes__[1:]:
                        cls.__id_for_second_id__[(k, d[k])] = prim_id

                return insts[0] if len(insts) == 1 else insts

            return wrapper

        return real_decorator

    @staticmethod
    def add_cache(return_type):
        def decorator(func):
            # noinspection PyProtectedMember
            def wrapper(cls, *args, **kwargs):

                data = func(cls, *args, **kwargs)
                if not data:
                    if return_type == 'object':
                        return None
                    elif return_type == 'list':
                        return []

                if not isinstance(data, list):
                    data = [data]

                insts = []
                for d in data:
                    inst = cls.instantiate(d)

                    prim_key = cls.__cache_indexes__[0]
                    prim_id = d[prim_key]

                    inst.__last_demand = datetime.datetime.now()
                    cls.check_cache()
                    cls.__inst_cache__[cls.__name__][prim_id] = inst
                    insts.append(inst)

                if return_type == 'list':
                    return insts

                elif return_type == 'object':
                    return insts[0]

                return insts
            return wrapper
        return decorator

    @staticmethod
    def update_cache(func):
        """decorator that returns the given values
                if they exits in the cache.
                Make sure to use parenthesis when using the decorator."""
        def wrapper(self, *args, **kwargs):

            # Execute the function and update the cache
            # Query the value
            prim_key = self.__cache_indexes__[0]

            inst = func(self, *args, **kwargs)
            prim_id = getattr(inst, self.__cache_indexes__[0])
            inst.__last_demand = datetime.datetime.now()
            self.check_cache()
            self.__inst_cache__[self.__name__][prim_id] = inst
            return inst

        return wrapper

    @classmethod
    def from_session_id(cls, sid):
        try:
            return cls.__inst_cache__[cls.__name__][
                cls.__id_for_session_id__[sid]]
        except KeyError:
            return None

    def set_session_id(self, session_id):
        """Attributes a session id to the instance.
        If the instance is put in the cache if not in it."""

        self._session_id = session_id
        prim_id = self._data[self.__cache_indexes__[0]]

        if session_id not in self.__id_for_session_id__:
            # Not in cache
            self.check_cache()
            self.__inst_cache__[self.__class__.__name__][prim_id] = self
        else:
            self.__id_for_session_id__.pop(session_id)

        # Update the session_id
        self.__id_for_session_id__[session_id] = prim_id
