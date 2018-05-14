import time
import unittest

from cache import CacheManager


def first_arg(a):
    return a


class TestCache(unittest.TestCase):
    cache_manager = CacheManager()

    @staticmethod
    @cache_manager.cache()
    def from_first_id(first_id):
        return {'first_id': 1, 'second_id': 'second_1'}

    @staticmethod
    @cache_manager.cache(first_arg)
    def from_first_id(first_id):
        return {'first_id': 1, 'second_id': 'second_1'}

    def test_cache_adding(self):
        # Test caching works
        inst1 = TestCache.from_first_id(1)

        # The cache must contains something

        inst_from_cache = TestCache.from_first_id(1)

        assert inst1 is inst_from_cache

    def test_cache_removal(self):
        # All cache delete
        TestCache.from_first_id(1)
        TestCache.cache_manager.reset_cache()
        assert len(TestCache.cache_manager._cache_content) == 0
