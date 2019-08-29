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

DUMMY_ONLY = """
modules:
  - "./:dummy_module"
test1:
  type: dummy
  test: test1
  only:
    env: prod
"""

DUMMY_ONLY_LIST = """
modules:
  - "./:dummy_module"
test1:
  type: dummy
  test: test1
  only:
    env:
      - int
      - prod
"""


DUMMY_EXCEPT = """
modules:
  - "./:dummy_module"
test1:
  type: dummy
  test: test1
  except:
    env: test
"""

DUMMY_EXCEPT_LIST = """
modules:
  - "./:dummy_module"
test1:
  type: dummy
  test: test1
  except:
    env:
     - test
     - int
"""

DUMMY_EXCEPT_DEPENDENCY = """
modules:
  - "./:dummy_module"
test1:
  type: dummy
  test: test1
  except:
    env: test

test2:
  type: dummy
  test: test2

test3:
  type: dummy
  test: test3
  dependencies:
    - test1
    - test2
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

LOOP = """
modules:
    - "./:dummy_module"
loop:
  type: dummy
  test: bla
  loop:
    foo:
      - a
      - b
    bar:
      - c
      - d
"""

LOOP_TEMPLATE_NAME = """
modules:
    - "./:dummy_module"
"{{foo}}-loop":
  type: dummy
  test: bla
  loop:
    foo:
      - a
      - b
"""


@mock.patch("dcosdeploy.auth.get_base_url", lambda: "/bla")
@mock.patch("dcosdeploy.config.reader.calculate_predefined_variables", lambda: dict())
class ConfigTest(unittest.TestCase):
    def test_marathon_simple(self):
        config, _ = read_config_mocked_open(dict(), MARATHON_SIMPLE, "{}")
        self.assertTrue("test1" in config)
        self.assertEqual(config["test1"].entity.app_id, "/hello")
        self.assertEqual(config["test1"].entity.app_definition, {})
        self.assertTrue(config["test1"].dependencies == list())

    def test_marathon_variables(self):
        config, _ = read_config_mocked_open(dict(env="test"), MARATHON_VARIABLES, MARATHON_VARIABLES_APP_DEF)
        self.assertTrue("test1" in config)
        self.assertEqual(config["test1"].entity.app_id, "/hello/test")
        self.assertEqual(config["test1"].entity.app_definition, {"id": "/hello/test", "cmd": "echo test"})

    def test_only(self):
        config, _ = read_config_mocked_open(dict(env="test"), DUMMY_ONLY)
        self.assertTrue("test1" not in config)
        config, _ = read_config_mocked_open(dict(env="prod"), DUMMY_ONLY)
        self.assertTrue("test1" in config)

    def test_only_list(self):
        config, _ = read_config_mocked_open(dict(env="test"), DUMMY_ONLY_LIST)
        self.assertTrue("test1" not in config)
        config, _ = read_config_mocked_open(dict(env="int"), DUMMY_ONLY_LIST)
        self.assertTrue("test1" in config)

    def test_except(self):
        config, _ = read_config_mocked_open(dict(env="test"), DUMMY_EXCEPT)
        self.assertTrue("test1" not in config)
        config, _ = read_config_mocked_open(dict(env="int"), DUMMY_EXCEPT)
        self.assertTrue("test1" in config)

    def test_except_list(self):
        config, _ = read_config_mocked_open(dict(env="test"), DUMMY_EXCEPT_LIST)
        self.assertTrue("test1" not in config)
        config, _ = read_config_mocked_open(dict(env="prod"), DUMMY_EXCEPT_LIST)
        self.assertTrue("test1" in config)

    def test_except_dependency(self):
        config, _ = read_config_mocked_open(dict(env="test"), DUMMY_EXCEPT_DEPENDENCY)
        self.assertTrue("test1" not in config)
        self.assertTrue("test2" in config)
        self.assertTrue("test3" in config)
        self.assertTrue(("test2", "create") in config["test3"].dependencies)
        self.assertTrue(("test1", "create") not in config["test3"].dependencies)

    def test_custom_module(self):
        config, managers = read_config_mocked_open(dict(), CUSTOM_MODULE)
        self.assertTrue("dummy" in managers)
        self.assertTrue("test1" in config)
        self.assertTrue("test2" in config)
        self.assertEqual(len(config["test2"].dependencies), 1)
        self.assertCountEqual(("test1", "create"), config["test2"].dependencies[0])

    def test_include(self):
        config, _ = read_config_mocked_open(dict(), INCLUDE, INCLUDE_BLA, "{}")
        self.assertTrue("test1" in config)
        self.assertEqual(config["test1"].entity.app_id, "/hello")
        self.assertEqual(config["test1"].entity.app_definition, {})

    def test_preprocess_func(self):
        config, _ = read_config_mocked_open(dict(), PREPROCESS)
        self.assertTrue("test1" in config)
        self.assertTrue(config["test1"].entity.preprocess, False)
      
    def test_loop(self):
        config, _ = read_config_mocked_open(dict(), LOOP)
        self.assertEqual(len(config), 4)
        self.assertTrue("loop-a-c" in config)
        self.assertTrue("loop-a-d" in config)
        self.assertTrue("loop-b-c" in config)
        self.assertTrue("loop-b-d" in config)

    def test_loop_template_name(self):
        config, _ = read_config_mocked_open(dict(), LOOP_TEMPLATE_NAME)
        self.assertEqual(len(config), 2)
        self.assertTrue("a-loop" in config)
        self.assertTrue("b-loop" in config)

    def test_confighelper_prepare_extra_vars(self):
        helper = config.ConfigHelper(dict(foo="bar"), dict())
        vars = helper.prepare_extra_vars({"a": "b", "foo:bar": {"abc": "xyz"}, "foo:baz": {"abc": "abc"}})
        self.assertEqual(vars, dict(abc="xyz", a="b"))


def read_config_mocked_open(provided_variables, *input_texts):
    open_mock = mock.mock_open(read_data=input_texts[0])
    open_mock.side_effect = [mock.mock_open(read_data=text).return_value for text in input_texts]
    with mock.patch('builtins.open', open_mock):
        return config.read_config("dcos-test.yaml", provided_variables)
