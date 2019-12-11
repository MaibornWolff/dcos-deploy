import unittest
from unittest import mock
from dcosdeploy.config import VariableContainer, ConfigHelper
from dcosdeploy.util import global_config


global_config.silent = True


VARS_YAML = """
defaults:
  hello: world
instances:
  test1:
    blub: bla
"""


@mock.patch("dcosdeploy.auth.get_base_url", lambda: "/bla")
class AppsTest(unittest.TestCase):
    def test_template_instances(self):
        from dcosdeploy.modules.apps import parse_config, preprocess_config, MarathonApp
        variables = VariableContainer(dict())
        config_helper = ConfigHelper(variables, None)
        config_helper.set_base_path(".")
        open_mock = mock.mock_open(read_data=VARS_YAML)
        open_mock.side_effect = [open_mock.return_value, mock.mock_open(read_data='{"id": "/hello/{{hello}}"}').return_value]
        with mock.patch('builtins.open', open_mock):
            config = list(preprocess_config("multi", dict(_vars="bla.yaml", _template="bla.json"), config_helper))
            self.assertEqual("multi-test1", config[0][0])
            config_helper.set_extra_vars(config[0][1]["extra_vars"])
            service = parse_config(config[0][0], config[0][1], config_helper)
        self.assertIsNotNone(service)
        self.assertTrue(isinstance(service, MarathonApp))
        self.assertEqual(service.app_id, "/hello/world")
