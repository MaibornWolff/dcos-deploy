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

    @mock.patch("dcosdeploy.modules.apps.MarathonAdapter")
    def test_dry_run(self, marathon_mock):
        global_config.silent = True
        marathon_mock.return_value.get_app_state.side_effect = lambda x: dict(id="/foo/bar", cpus=0.2, mem=128) if x == "/foo/bar" else None
        from dcosdeploy.modules.apps import MarathonAppsManager, MarathonApp
        app_config = MarathonApp("foobar", "/foo/bar", dict(id="/foo/bar", cpus=0.1, mem=128))
        app_config_unchanged = MarathonApp("foobar", "/foo/bar", dict(id="/foo/bar", cpus=0.2, mem=128))
        app_config_new = MarathonApp("foobar", "/foo/baz", dict(id="/foo/baz", cpus=0.1, mem=128))
        under_test = MarathonAppsManager()
        self.assertTrue(under_test.dry_run(app_config))
        self.assertFalse(under_test.dry_run(app_config_unchanged))
        self.assertTrue(under_test.dry_run(app_config_unchanged, dependencies_changed=True))
        self.assertTrue(under_test.dry_run(app_config_new))

    @mock.patch("dcosdeploy.modules.apps.MarathonAdapter")
    def test_dry_delete(self, marathon_mock):
        global_config.silent = True
        marathon_mock.return_value.get_app_state.side_effect = lambda x: dict(id="/foo/bar", cpus=0.1, mem=128) if x == "/exists" else None
        from dcosdeploy.modules.apps import MarathonAppsManager, MarathonApp
        app_config_exists = MarathonApp("foobar", "/exists", dict(id="/exists", cpus=0.1, mem=128))
        app_config_notexists = MarathonApp("foobar", "/foobar", dict(id="/foobar", cpus=0.1, mem=128))
        under_test = MarathonAppsManager()
        self.assertTrue(under_test.dry_delete(app_config_exists))
        self.assertFalse(under_test.dry_delete(app_config_notexists))

    @mock.patch("dcosdeploy.modules.apps.MarathonAdapter")
    def test_deploy(self, marathon_mock):
        global_config.silent = True
        marathon_mock.return_value.deploy_app.side_effect = lambda app_def, wait_for_deployment, force: app_def["id"] == "/foo/bar"
        from dcosdeploy.modules.apps import MarathonAppsManager, MarathonApp
        app_config_changed = MarathonApp("foobar", "/foo/bar", dict(id="/foo/bar", cpus=0.1, mem=128))
        app_config_unchanged = MarathonApp("foobar", "/foo/baz", dict(id="/foo/baz", cpus=0.2, mem=128))
        under_test = MarathonAppsManager()
        # Normal deployment
        self.assertTrue(under_test.deploy(app_config_changed))
        # No change, no restart because dependencies_changed=False
        self.assertFalse(under_test.deploy(app_config_unchanged))
        # No change, restart because dependencies_changed=True
        self.assertTrue(under_test.deploy(app_config_unchanged, dependencies_changed=True))
        marathon_mock.return_value.restart_app.assert_called_once_with("/foo/baz", True, force=False)
        self.assertEqual(marathon_mock.return_value.deploy_app.call_count, 3)

    @mock.patch("dcosdeploy.modules.apps.MarathonAdapter")
    def test_delete(self, marathon_mock):
        global_config.silent = True
        marathon_mock.return_value.delete_app.side_effect = lambda app_id, wait_for_deployment, force: app_id == "/exists"
        from dcosdeploy.modules.apps import MarathonAppsManager, MarathonApp
        app_config_exists = MarathonApp("foobar", "/exists", dict(id="/exists", cpus=0.1, mem=128))
        app_config_notexists = MarathonApp("foobar", "/foobar", dict(id="/foobar", cpus=0.1, mem=128))
        under_test = MarathonAppsManager()
        self.assertTrue(under_test.delete(app_config_exists))
        self.assertFalse(under_test.delete(app_config_notexists))
        self.assertEqual(marathon_mock.return_value.delete_app.call_count, 2)
