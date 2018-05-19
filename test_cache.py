
import unittest
from cache import ClassCacheManager


data = [{'id': 0, 'name': "num0", 'type': "int"},
        {'id': 1, 'name': "num1", 'type': "int"},
        {'id': 2, 'name': "num1", 'type': "float"}]


class CacheTest(object):

    keys = [('id',), ('name', 'type')]

    @staticmethod
    def key_from_inst(inst):
        return (inst.uid,), (inst.name, inst.type)

    cache = ClassCacheManager(keys, key_from_inst.__func__)

    @classmethod
    @cache.cache_inst_from_key(keys[0])
    def from_id(cls, uid):

        for d in data:

            if d['id'] == uid:
                return cls(d['id'], d['name'], d['type'])

        assert False

    @classmethod
    @cache.cache_inst_from_key(keys[1])
    def from_name_and_type(cls, name, ttype):

        for d in data:

            if d['name'] == name and d['type'] == ttype:
                return cls(d['id'], d['name'], d['type'])

        assert False

    @classmethod
    @cache.cache_inst_from_condition()
    def from_type(cls, type_name):

        res = []

        for d in data:
            if d['type'] == type_name:
                res.append(cls(d['id'], d['name'], d['type']))

        return res

    def __init__(self, uid, name, class_type):
        self._id = uid
        self._name = name
        self._type = class_type

    @property
    def uid(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type


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