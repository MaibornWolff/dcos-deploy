import json
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from ..base import ConfigurationException
from ..util.output import echo
from ..adapters.bouncer import BouncerAdapter
from ..adapters.secrets import SecretsAdapter
from .iam_users import IamUserBaseManager, render_permissions


LOGIN_ENDPOINT = "https://leader.mesos/acs/api/v1/auth/login"


class ServiceAccount(object):
    def __init__(self, name, secret, groups, permissions):
        self.name = name
        self.secret = secret
        self.groups = groups
        self.permissions = permissions


def parse_config(name, config, config_helper):
    name = config.get("name")
    if not name:
        raise ConfigurationException("name is required for serviceaccounts")
    secret_path = config.get("secret")
    name = config_helper.render(name)
    secret_path = config_helper.render(secret_path)
    groups = config.get("groups", list())
    permissions = render_permissions(config_helper, config.get("permissions", dict()))
    groups = [config_helper.render(g) for g in groups]
    return ServiceAccount(name, secret_path, groups, permissions)


class AccountsManager(IamUserBaseManager):
    def __init__(self):
        super().__init__()
        self.secrets = SecretsAdapter()

    def _does_serviceaccount_exist(self, name):
        return self.bouncer.get_account(name) is not None

    def _create_serviceaccount(self, name, secret):
        private_key, public_key = self._generate_keypair()
        self.bouncer.create_service_account(name, "", public_key)
        cert_secret = json.dumps(dict(login_endpoint=LOGIN_ENDPOINT, private_key=private_key, scheme="RS256", uid=name))
        self.secrets.write_secret(secret, cert_secret, update=False)

    def _generate_keypair(self, size=2048):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=size, backend=default_backend())
        private_key_string = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                                       format=serialization.PrivateFormat.PKCS8,
                                                       encryption_algorithm=serialization.NoEncryption())
        public_key = private_key.public_key()
        public_key_string = public_key.public_bytes(serialization.Encoding.PEM,
                                                    serialization.PublicFormat.SubjectPublicKeyInfo)
        return private_key_string.decode("utf-8"), public_key_string.decode("utf-8")

    def deploy(self, config, dependencies_changed=False, force=False):
        changed = False
        if not self._does_serviceaccount_exist(config.name):
            echo("\tCreating serviceaccount")
            self._create_serviceaccount(config.name, config.secret)
            changed = True
        else:
            echo("\tServiceaccount already exists. Not creating it.")

        if self._update_groups_permissions(config.name, config.groups, config.permissions):
            changed = True

        return changed

    def dry_run(self, config, dependencies_changed=False):
        if not self._does_serviceaccount_exist(config.name):
            echo("Would create serviceaccount %s" % config.name)
            return True
        return self._check_groups_permissions(config.name, config.groups, config.permissions)

    def delete(self, config, force=False):
        echo("\tDeleting serviceaccount secret")
        self.secrets.delete_secret(config.secret)
        echo("\tDeleting account")
        self.bouncer.delete_account(config.name)
        echo("\tDeletion complete.")
        return True

    def dry_delete(self, config):
        if self._does_serviceaccount_exist(config.name):
            echo("Would delete serviceaccount %s" % config.name)
            return True
        else:
            return False


__config__ = ServiceAccount
__manager__ = AccountsManager
__config_name__ = "serviceaccount"
