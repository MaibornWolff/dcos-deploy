import unittest
from unittest import mock
from dcosdeploy.config import VariableContainer

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
        open_mock = mock.mock_open(read_data=VARS_YAML)
        open_mock.side_effect = [open_mock.return_value, mock.mock_open(read_data='{"id": "/hello/{{hello}}"}').return_value]
        with mock.patch('builtins.open', open_mock):
            config = list(preprocess_config("multi", dict(_vars="bla.yaml", _template="bla.json")))
            self.assertEqual("multi-test1", config[0][0])
            service = parse_config(config[0][0], config[0][1], variables)
        self.assertIsNotNone(service)
        self.assertTrue(isinstance(service, MarathonApp))
        self.assertEqual(service.app_id, "/hello/world")
