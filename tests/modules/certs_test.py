import unittest
from unittest import mock


SIMPLE_YAML = """
mycert:
  type: cert
  cert_secret: myapp/admin_cert
  key_secret: myapp/admin_key
  dn: CN=admin
  hostnames:
    - admin.myapp
    - admin2.myapp
"""


@mock.patch("dcosdeploy.auth.get_base_url", lambda: "/bla")
class CertsTest(unittest.TestCase):
    def ignore_test_config_parse(self):
        from dcosdeploy.config import read_config
        with mock.patch('builtins.open', mock.mock_open(read_data=SIMPLE_YAML)):
            parsed_config, dependencies, managers = read_config("dcos-test.yaml", dict())
        self.assertTrue("cert:mycert" in parsed_config)
        cert = parsed_config["cert:mycert"]
        self.assertEqual("myapp/admin_cert", cert.cert_secret)
        self.assertEqual("myapp/admin_key", cert.key_secret)
        self.assertEqual("CN=admin", cert.dn)
        self.assertCountEqual(("admin.myapp", "admin2.myapp"), cert.hostnames)

    def ignore_test_existing_cert(self):
        from dcosdeploy.modules.certs import Cert, CertsManager
        cert = Cert("mycert", "cert_bla", "key_bla", {"CN": "foo"}, list())
        from dcosdeploy.adapters.secrets import SecretsAdapter
        m = mock.Mock()
        m.side_effect = [True, True]
        with mock.patch.object(SecretsAdapter, 'get_secret', m):
            certs = CertsManager()
            self.assertFalse(certs.deploy(cert))

    @mock.patch("dcosdeploy.modules.certs.CAAdapter")
    @mock.patch("dcosdeploy.modules.certs.SecretsAdapter")
    def test_half_existing_cert(self, mock_secretsadapter, mock_caadapter):
        # given
        mock_caadapter.return_value.generate_key.side_effect = lambda x, y: ("csr", "key")
        mock_caadapter.return_value.sign_csr.return_value = "cert"
        mock_secretsadapter.return_value.get_secret.side_effect = lambda name: True if name == "cert_bla" else False
        # when
        from dcosdeploy.modules.certs import Cert, CertsManager
        cert = Cert("mycert", "cert_bla", "key_bla", {"CN": "foo"}, list())
        certs = CertsManager()
        result = certs.deploy(cert, silent=True)
        # then
        self.assertTrue(result)
        mock_secretsadapter.return_value.delete_secret.assert_called_with("cert_bla")
        mock_secretsadapter.return_value.write_secret.assert_any_call('key_bla', file_content='key', update=False)
        mock_secretsadapter.return_value.write_secret.assert_any_call('cert_bla', file_content='cert', update=False)

    @mock.patch("dcosdeploy.modules.certs.CAAdapter")
    @mock.patch("dcosdeploy.modules.certs.SecretsAdapter")
    def test_deploy(self, mock_secretsadapter, mock_caadapter):
        # given
        mock_caadapter.return_value.generate_key.side_effect = lambda x, y: ("csr", "key")
        mock_caadapter.return_value.sign_csr.return_value = "cert"
        mock_secretsadapter.return_value.get_secret.side_effect = lambda x: False
        # when
        from dcosdeploy.modules.certs import Cert, CertsManager
        cert = Cert("mycert", "cert_bla", "key_bla", {"CN": "foo"}, list())
        certs = CertsManager()
        result = certs.deploy(cert, silent=True)
        # then
        self.assertTrue(result)
        mock_secretsadapter.return_value.delete_secret.assert_not_called()
        mock_secretsadapter.return_value.write_secret.assert_any_call('key_bla', file_content='key', update=False)
        mock_secretsadapter.return_value.write_secret.assert_any_call('cert_bla', file_content='cert', update=False)
