import base64
import io
import os
import unittest
from unittest import mock
from dcosdeploy.util import diff, global_config


DICT_DIFF = """    --- 
    +++ 
    @@ -1,4 +1,4 @@
     {
    -  "a": "1",
    -  "b": "2"
    +  "a": "2",
    +  "b": "1"
     }"""

TEXT = """foobar
bla
baz
"""

TEXT_DIFF = """    --- 
    +++ 
    @@ -1,3 +1,3 @@
     foobar
     bla
    -baz
    +bar"""


B64_DIFF = """    --- 
    +++ 
    @@ -1,7 +1,6 @@
     {
       "a": 1,
       "b": {
    -    "some_b64": "foobar
    -baz"
    +    "some_b64": "baz"
       }
     }"""

class DiffTest(unittest.TestCase):
    def test_compare_dicts(self):
        global_config.color_diffs = False
        # equal
        left = dict(a="1", b="2")
        right = dict(b="1", a="2")
        self.assertIsNone(diff.compare_dicts(left, left))
        # not equal
        result = diff.compare_dicts(left, right)
        self.assertEqual(result, DICT_DIFF)
        # base64 field
        left = dict(a=1, b=dict(some_b64=_b64("foobar\nbaz")))
        right = dict(a=1, b=dict(some_b64=_b64("baz")))
        result = diff.compare_dicts(left, right)
        self.assertEqual(result, B64_DIFF)

    def test_compare_text(self):
        # equal
        global_config.color_diffs = False
        self.assertIsNone(diff.compare_text(TEXT, TEXT))
        # not equal
        result = diff.compare_text(TEXT, TEXT.replace("baz", "bar"))
        self.assertEqual(result, TEXT_DIFF)

    def test_update_dict_with_defaults(self):
        my_dict = dict(a=1, b=2, c=dict(d=1, e=[1, 2, 3]))
        defaults = dict(d=1, b=4, c=dict(f=1, d=2))
        expected_result = dict(a=1, b=2, c=dict(d=1, e=[1, 2, 3], f=1), d=1)
        diff.update_dict_with_defaults(my_dict, defaults)
        self.assertDictEqual(my_dict, expected_result)


def _b64(text):
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")
