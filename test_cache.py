
import unittest
from cache import ClassCache


test_data = [{'id': 0, 'name': "num0", 'type': "int", 'value': 13},
             {'id': 1, 'name': "num1", 'type': "int", 'value': 15},
             {'id': 2, 'name': "num1", 'type': "float", 'value': 0.5}]


class CacheTest(object):

    # Cache related stuff
    keys = [('id',), ('name', 'type')]

    def key_from_inst(self):
        return (self.uid,), (self.name, self.type)

    cache = ClassCache(keys, key_from_inst)

    # Getters
    @classmethod
    @cache.cache_inst_from_key(keys[0])
    def from_id(cls, uid):

        for d in test_data:

            if d['id'] == uid:
                return cls(d['id'], d['name'], d['type'], d['value'])

        assert False

    @classmethod
    @cache.cache_inst_from_key(keys[1])
    def from_name_and_type(cls, name, ttype):

        for d in test_data:

            if d['name'] == name and d['type'] == ttype:
                return cls(d['id'], d['name'], d['type'], d['value'])

        assert False

    @classmethod
    @cache.cache_inst_from_condition()
    def from_type(cls, type_name):

        res = []

        for d in test_data:
            if d['type'] == type_name:
                res.append(cls(d['id'], d['name'], d['type'], d['value']))

        return res

    @classmethod
    @cache.cache_inst_from_condition()
    def from_value(cls, value):

        res = []

        for d in test_data:
            if d['value'] == value:
                res.append(cls(d['id'], d['name'], d['type'], d['value']))

        return res

    @classmethod
    @cache.insert()
    def create(cls, uid, name, class_type, value):
        d = {'id': uid, 'name': name, 'type': class_type, 'value': value}
        if d not in test_data:
            test_data.append(d)
            return cls(d['id'], d['name'], d['type'], d['value'])

    # Instance methods
    def __init__(self, uid, name, class_type, value):
        self._id = uid
        self._name = name
        self._type = class_type
        self._value = value

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


class TestCache(unittest.TestCase):

    def test_cache_adding(self):
        # Test caching works
        inst1 = CacheTest.from_id(1)

        # The cache must contains something

        inst_from_cache = CacheTest.from_name_and_type('num1', 'int')

        assert inst1 is inst_from_cache

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

        assert new_inst in insts
