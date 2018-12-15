import json
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from dcosdeploy.base import ConfigurationException
from dcosdeploy.util import print_if
from dcosdeploy.adapters.bouncer import BouncerAdapter
from dcosdeploy.adapters.secrets import SecretsAdapter


LOGIN_ENDPOINT = "https://leader.mesos/acs/api/v1/auth/login"


class ServiceAccount(object):
    def __init__(self, name, path, secret, groups, permissions):
        self.name = name
        self.path = path
        self.secret = secret
        self.groups = groups
        self.permissions = permissions
        self.dependencies = list()


def parse_config(name, config, config_helper):
    path = config.get("name")
    if not path:
        raise ConfigurationException("name is required for serviceaccounts")
    secret_path = config.get("secret")
    path = config_helper.render(path)
    secret_path = config_helper.render(secret_path)
    groups = config.get("groups", list())
    permissions = config.get("permissions", dict())
    groups = [config_helper.render(g) for g in groups]
    return ServiceAccount(name, path, secret_path, groups, permissions)


class AccountsManager(object):
    def __init__(self):
        self.bouncer = BouncerAdapter()
        self.secrets = SecretsAdapter()

    def does_serviceaccount_exist(self, path):
        return self.bouncer.get_account(path) is not None

    def create_serviceaccount(self, path, secret):
        private_key, public_key = self.generate_keypair()
        self.bouncer.create_account(path, "", public_key)
        cert_secret = json.dumps(dict(login_endpoint=LOGIN_ENDPOINT, private_key=private_key, scheme="RS256", uid=path))
        self.secrets.write_secret(secret, cert_secret, update=False)

    def generate_keypair(self, size=2048):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=size, backend=default_backend())
        private_key_string = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                                       format=serialization.PrivateFormat.PKCS8,
                                                       encryption_algorithm=serialization.NoEncryption())
        public_key = private_key.public_key()
        public_key_string = public_key.public_bytes(serialization.Encoding.PEM,
                                                    serialization.PublicFormat.SubjectPublicKeyInfo)
        return private_key_string.decode("utf-8"), public_key_string.decode("utf-8")

    def deploy(self, config, dependencies_changed=False, silent=False):
        changed = False
        if not self.does_serviceaccount_exist(config.path):
            print_if(not silent, "\tCreating serviceaccount")
            self.create_serviceaccount(config.path, config.secret)
            changed = True
        else:
            print_if(not silent, "\tServiceaccount already exists. Not creating it.")
        existing_groups = self.bouncer.get_groups_for_user(config.path)
        existing_permissions = self.bouncer.get_permissions_for_user(config.path)
        print_if(not silent, "\tUpdating groups")
        # Update groups
        for group in existing_groups:
            if group not in config.groups:
                self.bouncer.remove_user_from_group(config.path, group)
                changed = True
        for group in config.groups:
            if group not in existing_groups:
                self.bouncer.add_user_to_group(config.path, group)
                changed = True
        # Update permissions
        print_if(not silent, "\tUpdating permissions")
        for rid, actions in existing_permissions.items():
            target_actions = config.permissions.get(rid, list())
            for action in actions:
                if action not in target_actions:
                    self.bouncer.remove_permission_from_user(config.path, rid, action)
                    changed = True
        for rid, actions in config.permissions.items():
            for action in actions:
                if action not in existing_permissions.get(rid, list()):
                    self.bouncer.add_permission_to_user(config.path, rid, action)
                    changed = True
        return changed

    def dry_run(self, config, dependencies_changed=False, print_changes=True, debug=False):
        if not self.does_serviceaccount_exist(config.path):
            print("Would create serviceaccount %s" % config.path)
            return True
        existing_groups = self.bouncer.get_groups_for_user(config.path)
        existing_permissions = self.bouncer.get_permissions_for_user(config.path)

        changes = False
        # Check groups
        for group in existing_groups:
            if group not in config.groups:
                print("Would remove user %s from group %s" % (config.path, group))
                changes = True
        for group in config.groups:
            if group not in existing_groups:
                print("Would add user %s to group %s" % (config.path, group))
                changes = True
        # Check permissions
        for rid, actions in existing_permissions.items():
            if rid not in config.permissions:
                print("Would remove permission %s completely from user %s" % (rid, config.path))
                changes = True
            else:
                for action in actions:
                    if action not in config.permissions[rid]:
                        print("Would remove permission %s %s from user %s" % (rid, action, config.path))
                        changes = True
        for rid, actions in config.permissions.items():
            for action in actions:
                if action not in existing_permissions.get(rid, list()):
                    print("Would add permission %s %s to user %s" % (rid, action, config.path))
                    changes = True
        return changes


__config__ = ServiceAccount
__manager__ = AccountsManager
__config_name__ = "serviceaccount"
