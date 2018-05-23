
import unittest
from cache import CacheClassType, SessionCacheClassType


test_data = [{'id': 0, 'name': "num0", 'type': "int", 'value': 13},
             {'id': 1, 'name': "num1", 'type': "int", 'value': 15},
             {'id': 2, 'name': "num1", 'type': "float", 'value': 0.5},
             {'id': 3}]


class CacheTest(CacheClassType):

    @classmethod
    def keys_names(cls):
        yield 'id'
        yield 'name_type'

    def keys_from_inst(self):
        yield self.uid
        yield self.name
        yield self.type

    # Getters
    @classmethod
    @CacheClassType.cache_inst_from_key('id')
    def from_id(cls, uid):

        for d in test_data:

            if d['id'] == uid:
                return cls(d)

    @classmethod
    @CacheClassType.cache_inst_from_key('id')
    def from_ids(cls, uids):

        for d in test_data:

            did = d['id']
            if did in uids:
                yield did

    @classmethod
    @CacheClassType.cache_inst_from_key('name_type')
    def from_name_and_type(cls, name, ttype):

        for d in test_data:

            if d['name'] == name and d['type'] == ttype:
                return cls(d)

        assert False

    @classmethod
    @CacheClassType.cache_inst_from_condition
    def from_type(cls, type_name):

        res = []

        for d in test_data:
            try:
                if d['type'] == type_name:
                    res.append(cls(d))
            except KeyError:
                pass

        return res

    @classmethod
    @CacheClassType.cache_inst_from_condition
    def from_value(cls, value):

        res = []

        for d in test_data:
            try:
                if d['value'] == value:
                    res.append(cls(d))
            except KeyError:
                pass

        return res

    @classmethod
    @CacheClassType.insert
    def create(cls, uid, name, class_type, value):
        d = {'id': uid, 'name': name, 'type': class_type, 'value': value}
        if d not in test_data:
            test_data.append(d)
            return cls(d)

    # Instance methods
    def __init__(self, data_dict):
        self._id = data_dict['id']
        try:
            self._name = data_dict['name']
        except KeyError:
            self._name = None

        try:
            self._type = data_dict['type']
        except KeyError:
            self._type = None

        try:
            self._value = data_dict['value']
        except KeyError:
            self._value = None

    @property
    def uid(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type

    @property
    def value(self):
        return self._value

    # @cache.update_cache_instance()
    @value.setter
    def value(self, new_value):
        self._value = new_value


class SessionCacheTest(CacheTest, SessionCacheClassType):
    pass


class TestCache(unittest.TestCase):

    def test_cache_retrieval(self):
        # Test caching works
        inst1 = CacheTest.from_id(1)

        # The cache must contains something
        inst_from_cache = CacheTest.from_id(1)
        assert inst1 is inst_from_cache

        # Test from another key
        inst_from_cache = CacheTest.from_name_and_type('num1', 'int')
        assert inst1 is inst_from_cache

        # Test with a instance with missing secondary keys
        inst1 = CacheTest.from_id(3)

        inst_from_cache = CacheTest.from_id(3)
        assert inst1 is inst_from_cache

        # Retest retrieval from an empty cache

    def test_condition_cache(self):

        inst1 = CacheTest.from_id(1)

        insts = CacheTest.from_type('int')

        assert inst1 in insts

        insts = CacheTest.from_type('int')

        assert inst1 in insts

    def test_update(self):

        inst1 = CacheTest.from_id(1)
        inst2 = CacheTest.from_id(1)

        insts = CacheTest.from_value(15)

        inst1.value = 456

        assert inst1 is inst2
        assert inst1.value == inst2.value
        assert inst1 in insts

    def test_insertion(self):

        inst = CacheTest.from_id(0)

        insts = CacheTest.from_value(13)

        assert inst in insts

        new_inst = CacheTest.create(5, 'test_name', 'int', 13)

        assert insts[0]

        assert new_inst in insts


class TestSessionCache(unittest.TestCase):

    def test_cache(self):
        inst = SessionCacheTest.from_id(0)

        # Test attribute
        inst.set_session_id('test')
        assert inst.__session_key__ == (SessionCacheTest.__name__, 'test')

        # Test recovery
        inst_session = SessionCacheTest.from_session_id('test')
        assert inst_session is inst

        # Test removal
        inst_session.remove_session_id()
        inst = SessionCacheTest.from_session_id('test')
        assert inst is None
