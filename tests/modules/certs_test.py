import unittest
from unittest import mock
from dcosdeploy.config import ConfigHelper, VariableContainer


@mock.patch("dcosdeploy.auth.get_base_url", lambda: "/bla")
class CertsTest(unittest.TestCase):
    def test_config_parse(self):
        from dcosdeploy.modules.certs import parse_config
        config_helper = ConfigHelper(VariableContainer(dict()), None)
        params = dict(cert_secret="myapp/admin_cert", key_secret="myapp/admin_key", dn=dict(CN="admin"), hostnames=["admin.myapp", "admin2.myapp"])
        cert = parse_config("mycert", params, config_helper)
        self.assertEqual("myapp/admin_cert", cert.cert_secret)
        self.assertEqual("myapp/admin_key", cert.key_secret)
        self.assertEqual("admin", cert.dn["CN"])
        self.assertCountEqual(("admin.myapp", "admin2.myapp"), cert.hostnames)

    def test_existing_cert(self):
        from dcosdeploy.modules.certs import Cert, CertsManager
        cert = Cert("mycert", "cert_bla", "key_bla", {"CN": "foo"}, list())
        from dcosdeploy.adapters.secrets import SecretsAdapter
        m = mock.Mock()
        m.side_effect = [True, True]
        with mock.patch.object(SecretsAdapter, 'get_secret', m):
            certs = CertsManager()
            self.assertFalse(certs.deploy(cert, silent=True))

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
