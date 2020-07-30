import io
import unittest
from unittest import mock
import requests_mock
from dcosdeploy.base import ConfigurationException
from dcosdeploy.util import file as util_file


YAML_DATA = """
foo:
    - bar
"""


class FileTest(unittest.TestCase):
    @mock.patch('os.path.exists')
    def test_detect_yml_file(self, exists_mock):
        exists_mock.side_effect = lambda x: x == "foo/bar.yml"
        self.assertEqual(util_file.detect_yml_file("foo/bar"), ["foo/bar.yml"])

        with self.assertRaises(ConfigurationException):
            util_file.detect_yml_file("foo/baz")

    def test_read_yaml(self):
        open_mock = mock.mock_open(read_data=YAML_DATA)
        with mock.patch('builtins.open', open_mock):
            data = util_file.read_yaml("foo.yml")
            self.assertEqual(dict(foo=["bar"]), data)
