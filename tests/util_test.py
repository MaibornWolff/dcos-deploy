import unittest
from dcosdeploy import util


class UtilTest(unittest.TestCase):
    def test_compare_dicts(self):
        self.assertTrue(util.compare_dicts({"a": 1}, {"a": 1}))
        self.assertFalse(util.compare_dicts({"a": 1}, {"a": 2}))
        self.assertFalse(util.compare_dicts({"a": 1}, {"b": 1}))

    def test_compare_lists(self):
        self.assertTrue(util.compare_lists([1, 2, 3], [1, 2, 3]))
        self.assertFalse(util.compare_lists([1, 2, 3], [2, 1, 3]))
        self.assertFalse(util.compare_lists([1, 2, 3], [1, 2]))
        self.assertFalse(util.compare_lists([1, 2, 3], []))
        self.assertTrue(util.compare_lists([{"a": 1}, {"b": 2}], [{"a": 1}, {"b": 2}]))
        self.assertFalse(util.compare_lists([{"a": 1}, {"b": 2}], [{"a": 2}, {"b": 1}]))
        self.assertFalse(util.compare_lists([{"a": 1}, {"b": 2}], [{"a": 2}]))
