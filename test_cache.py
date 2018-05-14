import time
import unittest

from cache import CacheManager


def first_arg(a, k): return a[0]


def direct_out(o): return o


class TestCache(unittest.TestCase):
    cache_manager = CacheManager(['first_id', 'second_id'])

    @staticmethod
    @cache_manager.cache('first_id', first_arg, direct_out)
    def from_first_id(first_id):
        return {'first_id': 1, 'second_id': 'second_1'}

    @staticmethod
    @cache_manager.cache('second_id', first_arg, direct_out)
    def from_second_id(second_id):
        return {'first_id': 1, 'second_id': 'second_1'}

    @staticmethod
    @cache_manager.cache('first_id', first_arg, direct_out)
    def from_first_id_but_no_second(first_id):
        return {'first_id': 2}

    @staticmethod
    @cache_manager.cache('first_id', first_arg, direct_out)
    def from_first_id_but_no_first(first_id):
        return {'no_first_id': 3}

    def test_cache_adding(self):
        # Test caching works
        inst1 = TestCache.from_first_id(1)

        # The cache must contains something

        inst_from_cache = TestCache.from_first_id(1)
        inst_from_side = TestCache.from_second_id('second_1')

        assert inst1 is inst_from_cache is inst_from_side

        inst2 = TestCache.from_first_id_but_no_second(2)
        inst_from_cache2 = TestCache.from_first_id(2)

        assert inst2 is inst_from_cache2

        with self.assertRaises(AssertionError) as ctx:
            TestCache.from_first_id_but_no_first(3)

        self.assertTrue("No primary key in result." in str(ctx.exception))

    def test_cache_removal(self):
        # All cache delete
        TestCache.from_first_id(1)
        TestCache.cache_manager.reset_cache()
        assert len(TestCache.cache_manager._cache_content) == 0
