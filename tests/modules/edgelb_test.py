import unittest
from unittest import mock
import oyaml
from dcosdeploy.config import VariableContainer, ConfigHelper
from dcosdeploy.util import global_config



global_config.silent = True

POOL_DEF = """
name: foo
haproxy:
  frontends:
    - bindPort: 80
      protocol: HTTP
  backends:
    - name: foobar
      protocol: HTTP
      services:
        - endpoint:
            type: ADDRESS
            address: "foo.bar"
            port: 80
"""

POOL_DEF_CHANGED = """
name: foo
haproxy:
  frontends:
    - bindPort: 80
      protocol: HTTP
  backends:
    - name: foobar
      protocol: HTTP
      services:
        - endpoint:
            type: ADDRESS
            address: "bar.foo"
            port: 80
"""

SERVER_POOL_DEF = """
name: foo
haproxy:
  frontends:
  - bindPort: 80
    protocol: HTTP
    bindAddress: 0.0.0.0
    certificates: []
    miscStrs: []
    name: frontend_0.0.0.0_80
    linkBackend:
      map: []
  backends:
  - name: foobar
    protocol: HTTP
    services:
    - endpoint:
        type: ADDRESS
        address: "foo.bar"
        port: 80
        check:
          enabled: true
      marathon: {}
      mesos: {}
    balance: roundrobin
    miscStrs: []
    rewriteHttp:
      request:
        forwardfor: true
        rewritePath: true
        setHostHeader: true
        xForwardedPort: true
        xForwardedProtoHttpsIfTls: true
      response:
        rewriteLocation: true
  stats:
    bindAddress: 0.0.0.0
constraints: hostname:UNIQUE
cpus: 0.9
cpusAdminOverhead: 0.1
disk: 256
virtualNetworks: []
role: slave_public
ports: []
memAdminOverhead: 32
mem: 992
type: static
secrets: []
"""


@mock.patch("dcosdeploy.auth.get_base_url", lambda: "/bla")
class EdgelbTest(unittest.TestCase):
    def test_parse_config(self):
        from dcosdeploy.modules import edgelb
        variables = VariableContainer(dict())
        config_helper = ConfigHelper(variables, None)
        config_helper.set_base_path(".")

        open_mock = mock.mock_open(read_data=POOL_DEF)
        with mock.patch('builtins.open', open_mock):
            pool_config = edgelb.parse_config("foobar", dict(pool="pool.yml", api_server="foo/edgelb"), config_helper)

        self.assertEqual(pool_config.name, "foo")
        self.assertEqual(pool_config.api_server, "foo/edgelb/api")

    @mock.patch("dcosdeploy.modules.edgelb.EdgeLbAdapter")
    def test_dry_run(self, mock_adapter):
        mock_adapter.return_value.get_pools.side_effect = lambda x: ["foo"]
        mock_adapter.return_value.get_pool.side_effect = lambda x, y: oyaml.safe_load(SERVER_POOL_DEF)
        from dcosdeploy.modules import edgelb
        manager = edgelb.EdgeLbPoolsManager()
        # not existing pool
        pool = edgelb.EdgeLbPool("edgelb/api", "bar", dict(), None)
        self.assertTrue(manager.dry_run(pool))
        # existing pool, no change
        pool = edgelb.EdgeLbPool("edgelb/api", "foo", oyaml.safe_load(POOL_DEF), None)
        self.assertFalse(manager.dry_run(pool))
        # existing pool, change
        pool = edgelb.EdgeLbPool("edgelb/api", "foo", oyaml.safe_load(POOL_DEF_CHANGED), None)
        self.assertTrue(manager.dry_run(pool))

    @mock.patch("dcosdeploy.modules.edgelb.EdgeLbAdapter")
    def test_dry_run_pingfailed(self, mock_adapter):
        mock_adapter.return_value.ping.side_effect = lambda x: False
        from dcosdeploy.modules import edgelb
        manager = edgelb.EdgeLbPoolsManager()
        pool = edgelb.EdgeLbPool("edgelb/api", "foo", dict(), None)
        self.assertTrue(manager.dry_run(pool))

    @mock.patch("dcosdeploy.modules.edgelb.EdgeLbAdapter")
    def test_deploy(self, mock_adapter):
        mock_adapter.return_value.get_pools.side_effect = lambda x: ["foo"]
        from dcosdeploy.modules import edgelb
        manager = edgelb.EdgeLbPoolsManager()
        # Test update
        pool = edgelb.EdgeLbPool("edgelb/api", "foo", oyaml.safe_load(POOL_DEF), "foobar")
        self.assertTrue(manager.deploy(pool))
        #mock_adapter.return_value.update_pool.assert_called_once()
        mock_adapter.return_value.update_pool_template.assert_called_with("edgelb/api", "foo", "foobar")
        # Test create
        pool = edgelb.EdgeLbPool("edgelb/api", "bar", oyaml.safe_load(POOL_DEF), None)
        self.assertTrue(manager.deploy(pool))
        #mock_adapter.return_value.create_pool.assert_called_once()

    @mock.patch("dcosdeploy.modules.edgelb.EdgeLbAdapter")
    def test_dry_delete(self, mock_adapter):
        mock_adapter.return_value.get_pools.side_effect = lambda x: ["foo"]
        from dcosdeploy.modules import edgelb
        manager = edgelb.EdgeLbPoolsManager()
        # Not existing pool
        pool = edgelb.EdgeLbPool("edgelb/api", "bar", dict(), None)
        self.assertFalse(manager.dry_delete(pool))
        # Existing pool
        pool = edgelb.EdgeLbPool("edgelb/api", "foo", dict(), None)
        self.assertTrue(manager.dry_delete(pool))

    @mock.patch("dcosdeploy.modules.edgelb.EdgeLbAdapter")
    def test_delete(self, mock_adapter):
        mock_adapter.return_value.delete_pool.side_effect = lambda api_sever, name: name == "foo"
        from dcosdeploy.modules import edgelb
        manager = edgelb.EdgeLbPoolsManager()
        # Existing pool
        pool = edgelb.EdgeLbPool("edgelb/api", "foo", dict(), None)
        self.assertTrue(manager.delete(pool))
        mock_adapter.return_value.delete_pool.assert_called_with("edgelb/api", "foo")
        # Not existing pool
        pool = edgelb.EdgeLbPool("edgelb/api", "bar", dict(), None)
        self.assertFalse(manager.delete(pool))
        mock_adapter.return_value.delete_pool.assert_called_with("edgelb/api", "bar")
