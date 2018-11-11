import unittest
from unittest import mock
from dcosdeploy import config
import dummy_module


MARATHON_SIMPLE = """
test1:
  type: app
  path: /hello
  marathon: bla.json
"""

MARATHON_VARIABLES = """
test1:
  type: app
  path: /hello/{{env}}
  marathon: bla.json
"""
MARATHON_VARIABLES_APP_DEF = """
{
    "id": "/hello/{{env}}",
    "cmd": "echo {{env}}"
}
"""

MARATHON_ONLY = """
test1:
  type: app
  only:
    env: prod
"""

MARATHON_EXCEPT = """
test1:
  type: app
  except:
    env: test
"""

CUSTOM_MODULE = """
modules:
    - "./:dummy_module"
test1:
  type: dummy
  test: bla
test2:
  type: dummy
  test: blub
  dependencies:
    - test1
"""

INCLUDE = """
includes:
  - bla.yml
"""

INCLUDE_BLA = """
test1:
  type: app
  path: /hello
  marathon: bla.json
"""

PREPROCESS = """
modules:
    - "./:dummy_module"
test1:
  type: dummy
  test: bla
  pre: bla
"""


@mock.patch("dcosdeploy.auth.get_base_url", lambda: "/bla")
class ConfigTest(unittest.TestCase):
    def test_marathon_simple(self):
        config, managers = read_config_mocked_open(dict(), MARATHON_SIMPLE, "{}")
        self.assertTrue("test1" in config)
        self.assertEqual(config["test1"].entity.app_id, "/hello")
        self.assertEqual(config["test1"].entity.app_definition, {})
        self.assertTrue(config["test1"].dependencies == list())

    def test_marathon_variables(self):
        config, managers = read_config_mocked_open(dict(env="test"), MARATHON_VARIABLES, MARATHON_VARIABLES_APP_DEF)
        self.assertTrue("test1" in config)
        self.assertEqual(config["test1"].entity.app_id, "/hello/test")
        self.assertEqual(config["test1"].entity.app_definition, {"id": "/hello/test", "cmd": "echo test"})

    def test_only(self):
        config, managers = read_config_mocked_open(dict(env="test"), MARATHON_ONLY)
        self.assertTrue("test1" not in config)

    def test_except(self):
        config, managers = read_config_mocked_open(dict(env="test"), MARATHON_EXCEPT)
        self.assertTrue("test1" not in config)

    def test_custom_module(self):
        config, managers = read_config_mocked_open(dict(), CUSTOM_MODULE)
        self.assertTrue("dummy" in managers)
        self.assertTrue("test1" in config)
        self.assertTrue("test2" in config)
        self.assertEqual(len(config["test2"].dependencies), 1)
        self.assertCountEqual(("test1", "create"), config["test2"].dependencies[0])

    def test_include(self):
        config, managers = read_config_mocked_open(dict(), INCLUDE, INCLUDE_BLA, "{}")
        self.assertTrue("test1" in config)
        self.assertEqual(config["test1"].entity.app_id, "/hello")
        self.assertEqual(config["test1"].entity.app_definition, {})

    def test_preprocess_func(self):
        config, managers = read_config_mocked_open(dict(), PREPROCESS)
        self.assertTrue("test1" in config)
        self.assertTrue(config["test1"].entity.preprocess, False)


def read_config_mocked_open(provided_variables, *input_texts):
    open_mock = mock.mock_open(read_data=input_texts[0])
    open_mock.side_effect = [mock.mock_open(read_data=text).return_value for text in input_texts]
    with mock.patch('builtins.open', open_mock):
        return config.read_config("dcos-test.yaml", provided_variables)
